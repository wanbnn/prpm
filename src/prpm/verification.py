from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from prpm.errors import PrpmError
from prpm.release import ReleaseBundle, file_sha256, load_release
from prpm.repository import Repository

PACKAGE_TARGET = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:(?:==|@)(?P<version>[A-Za-z0-9][A-Za-z0-9._+-]*))?$"
)


def verify_wheel(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise PrpmError(f"Wheel contém caminhos duplicados: {path.name}")
            records = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(records) != 1:
                raise PrpmError(f"Wheel deve conter um único RECORD: {path.name}")
            record_name = records[0]
            if archive.getinfo(record_name).file_size > 10 * 1024 * 1024:
                raise PrpmError(f"RECORD excessivamente grande: {path.name}")
            rows = list(
                csv.reader(
                    io.StringIO(archive.read(record_name).decode("utf-8"))
                )
            )
            checked = 0
            for row in rows:
                if len(row) != 3:
                    raise PrpmError("Linha inválida no RECORD do wheel.")
                filename, encoded_hash, size_text = row
                if filename == record_name:
                    continue
                if not encoded_hash:
                    raise PrpmError(f"RECORD sem hash para {filename}.")
                try:
                    algorithm, expected = encoded_hash.split("=", 1)
                    info = archive.getinfo(filename)
                    if info.file_size > 2 * 1024 * 1024 * 1024:
                        raise PrpmError(f"Arquivo interno excessivamente grande: {filename}")
                    hasher = hashlib.new(algorithm)
                    actual_size = 0
                    with archive.open(filename) as stream:
                        while chunk := stream.read(1024 * 1024):
                            hasher.update(chunk)
                            actual_size += len(chunk)
                    digest = hasher.digest()
                except (ValueError, KeyError, zipfile.BadZipFile) as exc:
                    raise PrpmError(f"Entrada inválida no wheel: {filename}") from exc
                actual = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
                if actual != expected:
                    raise PrpmError(f"Hash interno divergente no wheel: {filename}")
                if size_text and actual_size != int(size_text):
                    raise PrpmError(f"Tamanho interno divergente no wheel: {filename}")
                checked += 1
    except zipfile.BadZipFile as exc:
        raise PrpmError(f"Wheel inválido: {path.name}") from exc
    return {"filename": path.name, "recordEntries": checked}


def verify_local(directory_or_file: Path) -> dict[str, Any]:
    target = directory_or_file.resolve()
    if target.is_file():
        report: dict[str, Any] = {
            "scope": "file",
            "filename": target.name,
            "sha256": file_sha256(target),
            "size": target.stat().st_size,
        }
        if target.suffix == ".whl":
            report["wheel"] = verify_wheel(target)
        return report
    if not target.is_dir():
        raise PrpmError(f"Caminho não encontrado: {target}")
    bundle = load_release(target)
    wheels = [verify_wheel(path) for path in bundle.artifacts if path.suffix == ".whl"]
    return _bundle_report(bundle, wheels)


def verify_remote(target: str, repository: Repository) -> dict[str, Any]:
    match = PACKAGE_TARGET.fullmatch(target)
    if not match:
        raise PrpmError(
            "Pacote inválido. Use `nome`, `nome==versão` ou `nome@versão`."
        )
    name = match.group("name")
    requested_version = match.group("version")
    endpoint = (
        f"{repository.json_url}/{name}/{requested_version}/json"
        if requested_version
        else f"{repository.json_url}/{name}/json"
    )
    payload = _get_json(endpoint)
    version = str(payload.get("info", {}).get("version", ""))
    if requested_version and version != requested_version:
        raise PrpmError(f"O índice retornou a versão inesperada {version}.")
    files = payload.get("urls", [])
    if not files:
        raise PrpmError(f"Nenhum artefato publicado para {name}=={version}.")
    checked_files = []
    with tempfile.TemporaryDirectory(prefix="prpm-verify-") as temporary:
        temporary_path = Path(temporary)
        for item in files:
            filename = str(item["filename"])
            if not filename or Path(filename).name != filename:
                raise PrpmError("O índice retornou um nome de arquivo inseguro.")
            path = temporary_path / filename
            _download(str(item["url"]), path)
            expected = str(item.get("digests", {}).get("sha256", ""))
            actual = file_sha256(path)
            if not expected or actual != expected:
                raise PrpmError(f"SHA-256 do PyPI divergente: {filename}")
            file_report: dict[str, Any] = {
                "filename": filename,
                "sha256": actual,
                "size": path.stat().st_size,
            }
            if path.suffix == ".whl":
                file_report["wheel"] = verify_wheel(path)
            checked_files.append(file_report)
    return {
        "scope": "repository",
        "repository": repository.name,
        "name": str(payload["info"]["name"]),
        "version": version,
        "files": checked_files,
        "ownership": payload.get("ownership", {}),
    }


def _bundle_report(
    bundle: ReleaseBundle, wheels: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "scope": "release",
        "name": bundle.document["name"],
        "version": bundle.document["version"],
        "keyId": bundle.document["signing"]["keyId"],
        "signature": "valid",
        "artifacts": [
            {
                "filename": path.name,
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            }
            for path in bundle.artifacts
        ],
        "wheels": wheels,
    }


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "prpm"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise PrpmError("Pacote ou versão não encontrados no repositório.") from exc
        raise PrpmError(f"O repositório respondeu com HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise PrpmError(f"Não foi possível consultar o repositório: {exc.reason}") from exc


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "prpm"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            with destination.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
    except urllib.error.URLError as exc:
        raise PrpmError(f"Falha ao baixar {destination.name}: {exc.reason}") from exc
