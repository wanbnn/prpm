from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import tomlkit
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from prpm.errors import PrpmError

MANIFEST_NAME = "pyproject.toml"


def normalized_project_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    if not name:
        raise PrpmError("O nome do projeto não pode ficar vazio.")
    return name


def find_project(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / MANIFEST_NAME).is_file():
            return directory
    raise PrpmError("Nenhum pyproject.toml encontrado. Execute `prpm init` primeiro.")


def make_manifest(name: str, description: str = "") -> str:
    safe_name = normalized_project_name(name)
    return (
        "[project]\n"
        f'name = "{safe_name}"\n'
        'version = "0.1.0"\n'
        f'description = "{description}"\n'
        'requires-python = ">=3.10"\n'
        "dependencies = []\n\n"
        "[project.optional-dependencies]\n"
        "dev = []\n\n"
        "[tool.prpm.scripts]\n"
        'test = "python -m pytest"\n'
    )


class Manifest:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / MANIFEST_NAME
        if not self.path.is_file():
            raise PrpmError(f"{self.path} não existe.")
        try:
            self.document = tomlkit.parse(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PrpmError(f"pyproject.toml inválido: {exc}") from exc
        if "project" not in self.document:
            raise PrpmError("pyproject.toml precisa de uma seção [project].")

    @classmethod
    def discover(cls, start: Path | None = None) -> "Manifest":
        return cls(find_project(start))

    @property
    def name(self) -> str:
        return str(self.document["project"].get("name", self.root.name))

    @property
    def requires_python(self) -> str:
        return str(self.document["project"].get("requires-python", ""))

    def dependencies(self, dev: bool = False) -> list[str]:
        if dev:
            optional = self.document["project"].get("optional-dependencies", {})
            return [str(item) for item in optional.get("dev", [])]
        return [str(item) for item in self.document["project"].get("dependencies", [])]

    def all_dependencies(self, include_dev: bool = True) -> list[str]:
        values = self.dependencies(False)
        if include_dev:
            values.extend(self.dependencies(True))
        return values

    def scripts(self) -> dict[str, str | list[str]]:
        tool = self.document.get("tool", {})
        prpm = tool.get("prpm", {})
        scripts = prpm.get("scripts", {})
        return {str(key): value for key, value in scripts.items()}

    def add(self, requirement: str, dev: bool = False) -> None:
        parsed = _requirement(requirement)
        items = self._dependency_array(dev)
        target = canonicalize_name(parsed.name)
        kept = []
        replaced = False
        for item in items:
            existing = _requirement(str(item))
            if canonicalize_name(existing.name) == target:
                if not replaced:
                    kept.append(requirement)
                    replaced = True
            else:
                kept.append(str(item))
        if not replaced:
            kept.append(requirement)
        self._replace_array(items, kept)

    def remove(self, package: str, dev: bool | None = None) -> bool:
        target = canonicalize_name(_requirement(package).name)
        changed = False
        groups: Iterable[bool] = (False, True) if dev is None else (dev,)
        for group in groups:
            items = self._dependency_array(group)
            kept = [
                str(item)
                for item in items
                if canonicalize_name(_requirement(str(item)).name) != target
            ]
            if len(kept) != len(items):
                self._replace_array(items, kept)
                changed = True
        return changed

    def save(self) -> None:
        self.path.write_text(tomlkit.dumps(self.document), encoding="utf-8")

    def _dependency_array(self, dev: bool):
        project = self.document["project"]
        if dev:
            if "optional-dependencies" not in project:
                project["optional-dependencies"] = tomlkit.table()
            optional = project["optional-dependencies"]
            if "dev" not in optional:
                optional["dev"] = tomlkit.array().multiline(True)
            return optional["dev"]
        if "dependencies" not in project:
            project["dependencies"] = tomlkit.array().multiline(True)
        return project["dependencies"]

    @staticmethod
    def _replace_array(array, values: list[str]) -> None:
        del array[:]
        array.multiline(True)
        for value in values:
            array.append(value)


def _requirement(value: str) -> Requirement:
    try:
        return Requirement(value)
    except InvalidRequirement as exc:
        raise PrpmError(f"Dependência inválida: {value}") from exc
