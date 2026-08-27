from __future__ import annotations

import hashlib
import json
import platform
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from prpm.environment import ProjectEnvironment
from prpm.errors import PrpmError

LOCK_NAME = "prpm.lock"
LOCK_VERSION = 1
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def content_hash(requirements: list[str]) -> str:
    normalized = "\n".join(sorted(requirements))
    return "sha256:" + hashlib.sha256(normalized.encode()).hexdigest()


def resolution_environment() -> dict[str, str]:
    """Return the PEP 508 marker environment used by dependency resolution."""
    environment = default_environment()
    return {key: str(environment[key]) for key in sorted(environment)}


def _normalized_hash(value: str) -> str:
    value = value.strip()
    if ":" in value:
        algorithm, digest = value.split(":", 1)
        return f"{algorithm.lower()}:{digest.lower()}"
    if _SHA256.fullmatch(value):
        return f"sha256:{value.lower()}"
    raise PrpmError(f"Hash inválido no prpm.lock: {value!r}")


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
        if not self.exists():
            return False
        document = self.read()
        return (
            document.get("contentHash") == content_hash(requirements)
            and document.get("environment") == resolution_environment()
        )

    def resolve(
        self,
        environment: ProjectEnvironment,
        requirements: list[str],
        direct_requirements: list[str],
        production_requirements: list[str] | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        if not requirements:
            return self._document([], requirements)
        raw = self._resolve_report(environment, requirements, constraints)
        production = (
            requirements if production_requirements is None else production_requirements
        )
        production_raw = (
            raw
            if sorted(production) == sorted(requirements)
            else self._resolve_report(environment, production, constraints)
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
                    "hashes": sorted(
                        f"{algorithm.lower()}:{digest.lower()}"
                        for algorithm, digest in archive.get("hashes", {}).items()
                    ),
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

    def direct_pins(
        self,
        *,
        include_dev: bool = True,
        exclude_names: set[str] | None = None,
    ) -> list[str]:
        """Return exact requirements for direct dependencies retained during updates."""
        excluded = {canonicalize_name(name) for name in (exclude_names or set())}
        values = []
        for package in self.read().get("packages", []):
            if not package.get("direct", False):
                continue
            if not include_dev and package.get("dev", False):
                continue
            if canonicalize_name(package["name"]) in excluded:
                continue
            values.append(
                package.get("requirement")
                or f"{package['name']}=={package['version']}"
            )
        return values

    def hashed_requirements(self, include_dev: bool = True) -> list[str]:
        """Return requirements-file lines protected by lockfile hashes."""
        values = []
        missing = []
        for package in self.read().get("packages", []):
            if not include_dev and package.get("dev", False):
                continue
            requirement = package.get("requirement") or f"{package['name']}=={package['version']}"
            hashes = [_normalized_hash(value) for value in package.get("hashes", [])]
            if not hashes:
                missing.append(package["name"])
                continue
            hash_options = " ".join(f"--hash={value}" for value in sorted(set(hashes)))
            values.append(f"{requirement} {hash_options}")
        if missing:
            raise PrpmError(
                "Instalação com hashes exige hash para todos os pacotes; "
                f"ausente em: {', '.join(sorted(missing, key=str.lower))}. "
                "Regere o lockfile na plataforma atual ou desative PRPM_VERIFY_HASHES."
            )
        return values

    @staticmethod
    def _resolve_report(
        environment: ProjectEnvironment,
        requirements: list[str],
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        if not requirements:
            return {"install": []}
        with tempfile.TemporaryDirectory(prefix="prpm-resolve-") as temporary:
            report = Path(temporary) / "report.json"
            arguments = [
                "install",
                "--dry-run",
                "--ignore-installed",
                "--report",
                str(report),
            ]
            if constraints:
                constraints_file = Path(temporary) / "constraints.txt"
                constraints_file.write_text(
                    "\n".join(constraints) + "\n",
                    encoding="utf-8",
                )
                arguments.extend(["-c", str(constraints_file)])
            environment.pip([*arguments, *requirements], capture=True)
            return json.loads(report.read_text(encoding="utf-8"))

    @staticmethod
    def _document(packages: list[dict[str, Any]], requirements: list[str]) -> dict[str, Any]:
        return {
            "lockVersion": LOCK_VERSION,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "environment": resolution_environment(),
            "contentHash": content_hash(requirements),
            "packages": packages,
        }
