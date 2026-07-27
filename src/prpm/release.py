from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prpm.errors import PrpmError
from prpm.manifest import Manifest
from prpm.signing import (
    canonical_json,
    generate_identity,
    public_key_id,
    public_key_text,
    verify_signature,
)

MANIFEST_FILE = "prpm-manifest.json"
SIGNATURE_FILE = "prpm-manifest.sig"
RELEASE_SCHEMA = 1


@dataclass(frozen=True)
class ReleaseBundle:
    directory: Path
    manifest_path: Path
    signature_path: Path
    document: dict[str, Any]
    artifacts: tuple[Path, ...]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release(
    manifest: Manifest,
    output: Path | None = None,
    *,
    force: bool = False,
) -> ReleaseBundle:
    project = manifest.document["project"]
    version = str(project.get("version", "")).strip()
    if not version:
        raise PrpmError("A seção [project] precisa definir `version`.")
    if "build-system" not in manifest.document:
        raise PrpmError(
            "pyproject.toml precisa de [build-system] para publicar um pacote."
        )

    destination = (output or manifest.root / "dist").resolve()
    destination.mkdir(parents=True, exist_ok=True)
    identity = generate_identity()

    with tempfile.TemporaryDirectory(prefix="prpm-pack-") as temporary:
        temporary_path = Path(temporary)
        _run(
            [
                sys.executable,
                "-m",
                "build",
                "--outdir",
                str(temporary_path),
                str(manifest.root),
            ],
            manifest.root,
            "Falha ao construir o pacote",
        )
        built = tuple(
            sorted(
                (
                    path
                    for path in temporary_path.iterdir()
                    if path.is_file()
                    and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
                ),
                key=lambda path: path.name,
            )
        )
        if not built:
            raise PrpmError("O build não produziu wheel nem source distribution.")
        targets = tuple(destination / path.name for path in built)
        collisions = [
            path
            for path in (*targets, destination / MANIFEST_FILE, destination / SIGNATURE_FILE)
            if path.exists()
        ]
        if collisions and not force:
            names = ", ".join(path.name for path in collisions)
            raise PrpmError(f"Artefatos já existem: {names}. Use `prpm pack --force`.")
        for path in collisions:
            path.unlink()
        for source, target in zip(built, targets):
            shutil.copy2(source, target)

    _run(
        [sys.executable, "-m", "twine", "check", *map(str, targets)],
        manifest.root,
        "Os artefatos falharam no twine check",
    )

    artifacts = [
        {
            "filename": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
            "type": "wheel" if path.suffix == ".whl" else "sdist",
        }
        for path in targets
    ]
    urls = project.get("urls", {})
    document = {
        "schemaVersion": RELEASE_SCHEMA,
        "name": manifest.name,
        "version": version,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "requiresPython": str(project.get("requires-python", "")),
        "dependencies": manifest.dependencies(False),
        "source": {
            "repository": str(urls.get("Repository", "")),
        },
        "signing": {
            "algorithm": "ed25519",
            "keyId": identity.key_id,
            "publicKey": public_key_text(identity),
            "storage": "keyring" if identity.persistent else "ephemeral",
        },
        "artifacts": artifacts,
    }
    payload = canonical_json(document)
    signature_document = {
        "schemaVersion": RELEASE_SCHEMA,
        "algorithm": "ed25519",
        "keyId": identity.key_id,
        "signature": identity.sign(payload),
    }
    manifest_path = destination / MANIFEST_FILE
    signature_path = destination / SIGNATURE_FILE
    manifest_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    signature_path.write_text(
        json.dumps(signature_document, indent=2) + "\n",
        encoding="utf-8",
    )
    return ReleaseBundle(
        destination,
        manifest_path,
        signature_path,
        document,
        targets,
    )


def load_release(directory: Path) -> ReleaseBundle:
    root = directory.resolve()
    manifest_path = root / MANIFEST_FILE
    signature_path = root / SIGNATURE_FILE
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        signature = json.loads(signature_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PrpmError(
            f"Manifesto de release ausente em {root}. Execute `prpm pack`."
        ) from exc
    except json.JSONDecodeError as exc:
        raise PrpmError(f"Manifesto ou assinatura inválidos: {exc}") from exc
    if document.get("schemaVersion") != RELEASE_SCHEMA:
        raise PrpmError("Versão de manifesto PRPM não suportada.")
    signing = document.get("signing", {})
    if signature.get("keyId") != signing.get("keyId"):
        raise PrpmError("A assinatura não corresponde à chave do manifesto.")
    if public_key_id(str(signing.get("publicKey", ""))) != signing.get("keyId"):
        raise PrpmError("O identificador não corresponde à chave pública.")
    if not verify_signature(
        canonical_json(document),
        str(signature.get("signature", "")),
        str(signing.get("publicKey", "")),
    ):
        raise PrpmError("Assinatura Ed25519 inválida.")
    artifacts = []
    for item in document.get("artifacts", []):
        filename = str(item.get("filename", ""))
        if not filename or Path(filename).name != filename:
            raise PrpmError("O manifesto contém um nome de artefato inseguro.")
        path = root / filename
        if not path.is_file():
            raise PrpmError(f"Artefato ausente: {filename}")
        if path.stat().st_size != item.get("size"):
            raise PrpmError(f"Tamanho divergente: {filename}")
        if file_sha256(path) != item.get("sha256"):
            raise PrpmError(f"SHA-256 divergente: {filename}")
        artifacts.append(path)
    if not artifacts:
        raise PrpmError("O manifesto não contém artefatos.")
    return ReleaseBundle(
        root,
        manifest_path,
        signature_path,
        document,
        tuple(artifacts),
    )


def _run(command: list[str], cwd: Path, message: str) -> None:
    result = subprocess.run(command, cwd=cwd)
    if result.returncode:
        raise PrpmError(f"{message} (código {result.returncode}).")
