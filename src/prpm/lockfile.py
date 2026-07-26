from __future__ import annotations

import hashlib
import json
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from prpm.environment import ProjectEnvironment
from prpm.errors import PrpmError

LOCK_NAME = "prpm.lock"
LOCK_VERSION = 1


def content_hash(requirements: list[str]) -> str:
    normalized = "\n".join(sorted(requirements))
    return "sha256:" + hashlib.sha256(normalized.encode()).hexdigest()


class Lockfile:
    def __init__(self, root: Path):
        self.path = root / LOCK_NAME

    def exists(self) -> bool:
        return self.path.is_file()

    def read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PrpmError("prpm.lock não existe; execute `prpm install`.") from exc
        except json.JSONDecodeError as exc:
            raise PrpmError(f"prpm.lock inválido: {exc}") from exc
        if data.get("lockVersion") != LOCK_VERSION:
            raise PrpmError("Versão de prpm.lock não suportada.")
        return data

    def is_current(self, requirements: list[str]) -> bool:
        return self.exists() and self.read().get("contentHash") == content_hash(requirements)

    def resolve(
        self,
        environment: ProjectEnvironment,
        requirements: list[str],
        direct_requirements: list[str],
        production_requirements: list[str] | None = None,
    ) -> dict[str, Any]:
        if not requirements:
            return self._document([], requirements)
        raw = self._resolve_report(environment, requirements)
        production = (
            requirements if production_requirements is None else production_requirements
        )
        production_raw = (
            raw
            if sorted(production) == sorted(requirements)
            else self._resolve_report(environment, production)
        )
        production_names = {
            canonicalize_name(item["metadata"]["name"])
            for item in production_raw.get("install", [])
        }
        direct_by_name = {
            canonicalize_name(Requirement(value).name): Requirement(value)
            for value in direct_requirements
        }
        packages = []
        for item in raw.get("install", []):
            metadata = item["metadata"]
            name = metadata["name"]
            download = item.get("download_info", {})
            archive = download.get("archive_info", {})
            canonical_name = canonicalize_name(name)
            declared = direct_by_name.get(canonical_name)
            packages.append(
                {
                    "name": name,
                    "version": metadata["version"],
                    "direct": canonical_name in direct_by_name,
                    "dev": canonical_name not in production_names,
                    "requirement": (
                        str(declared)
                        if declared is not None and declared.url is not None
                        else f"{name}=={metadata['version']}"
                    ),
                    "url": download.get("url"),
                    "hashes": sorted(archive.get("hashes", {}).values()),
                }
            )
        packages.sort(key=lambda item: canonicalize_name(item["name"]))
        return self._document(packages, requirements)

    def write(self, document: dict[str, Any]) -> None:
        payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        self.path.write_text(payload, encoding="utf-8")

    def pinned_requirements(self, include_dev: bool = True) -> list[str]:
        values = []
        for package in self.read().get("packages", []):
            if not include_dev and package.get("dev", False):
                continue
            values.append(package.get("requirement") or f"{package['name']}=={package['version']}")
        return values

    @staticmethod
    def _resolve_report(
        environment: ProjectEnvironment, requirements: list[str]
    ) -> dict[str, Any]:
        if not requirements:
            return {"install": []}
        with tempfile.TemporaryDirectory(prefix="prpm-resolve-") as temporary:
            report = Path(temporary) / "report.json"
            environment.pip(
                [
                    "install",
                    "--dry-run",
                    "--ignore-installed",
                    "--report",
                    str(report),
                    *requirements,
                ],
                capture=True,
            )
            return json.loads(report.read_text(encoding="utf-8"))

    @staticmethod
    def _document(packages: list[dict[str, Any]], requirements: list[str]) -> dict[str, Any]:
        return {
            "lockVersion": LOCK_VERSION,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "contentHash": content_hash(requirements),
            "packages": packages,
        }
