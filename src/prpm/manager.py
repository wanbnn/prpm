from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from prpm.console import console
from prpm.environment import ProjectEnvironment
from prpm.errors import PrpmError
from prpm.lockfile import Lockfile
from prpm.manifest import Manifest


class PackageManager:
    def __init__(self, manifest: Manifest):
        self.manifest = manifest
        self.environment = ProjectEnvironment(manifest.root)
        self.lockfile = Lockfile(manifest.root)

    def install(self, include_dev: bool = True, frozen: bool = False) -> None:
        all_requirements = self.manifest.all_dependencies(True)
        requirements = self.manifest.all_dependencies(include_dev)
        if not self.environment.satisfies_python(self.manifest.requires_python):
            raise PrpmError(
                f"Python atual não satisfaz {self.manifest.requires_python}."
            )
        self.environment.ensure()
        if frozen:
            if not self.lockfile.is_current(all_requirements):
                raise PrpmError(
                    "prpm.lock está ausente ou desatualizado; remova --frozen para regenerá-lo."
                )
            selected = self.lockfile.pinned_requirements(include_dev)
        else:
            console.info("Resolvendo dependências")
            document = self.lockfile.resolve(
                self.environment,
                all_requirements,
                self.manifest.all_dependencies(True),
                self.manifest.dependencies(False),
            )
            self.lockfile.write(document)
            selected = requirements
        if selected:
            console.info(f"Instalando {len(selected)} pacote(s)")
            self.environment.pip(["install", *selected])
        console.success("Dependências instaladas")

    def add(self, specifications: list[str], dev: bool = False) -> None:
        self.environment.ensure()
        console.info(f"Resolvendo {', '.join(specifications)}")
        self.environment.pip(["install", *specifications])
        installed = {
            canonicalize_name(name): version
            for name, version in self.environment.installed().items()
        }
        for specification in specifications:
            requirement = Requirement(specification)
            saved = specification
            if not requirement.specifier and requirement.url is None:
                version = installed.get(canonicalize_name(requirement.name))
                if version:
                    saved = f"{requirement.name}>={version}"
            self.manifest.add(saved, dev)
        self.manifest.save()
        self._refresh_lock()
        group = "desenvolvimento" if dev else "produção"
        console.success(f"Dependências de {group} adicionadas")

    def remove(self, packages: list[str], dev: bool | None = None) -> None:
        missing = []
        names = []
        for package in packages:
            requirement = Requirement(package)
            names.append(requirement.name)
            if not self.manifest.remove(package, dev):
                missing.append(requirement.name)
        if missing:
            raise PrpmError(f"Não encontrado no manifesto: {', '.join(missing)}")
        self.manifest.save()
        self.environment.pip(["uninstall", "-y", *names], check=False)
        self.install(include_dev=True)
        console.success(f"Removido: {', '.join(names)}")

    def update(self, packages: list[str], include_dev: bool = True) -> None:
        declared = self.manifest.all_dependencies(include_dev)
        if packages:
            targets = {canonicalize_name(Requirement(item).name) for item in packages}
            declared = [
                item
                for item in declared
                if canonicalize_name(Requirement(item).name) in targets
            ]
            if not declared:
                raise PrpmError("Nenhum dos pacotes informados está no manifesto.")
        if declared:
            self.environment.pip(["install", "--upgrade", *declared])
        self._refresh_lock()
        console.success("Dependências atualizadas")

    def list_packages(self, depth: int = 0) -> list[dict[str, str]]:
        result = self.environment.pip(
            ["list", "--format=json", "--not-required"] if depth == 0 else ["list", "--format=json"],
            capture=True,
        )
        ignored = {"pip", "setuptools", "wheel"}
        return [
            package
            for package in json.loads(result.stdout)
            if canonicalize_name(package["name"]) not in ignored
        ]

    def _refresh_lock(self) -> None:
        requirements = self.manifest.all_dependencies(True)
        document = self.lockfile.resolve(
            self.environment,
            requirements,
            self.manifest.all_dependencies(True),
            self.manifest.dependencies(False),
        )
        self.lockfile.write(document)


def package_info(package: str) -> dict:
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise PrpmError(f"Pacote não encontrado no PyPI: {package}") from exc
        raise PrpmError(f"PyPI respondeu com HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise PrpmError(f"Não foi possível consultar o PyPI: {exc.reason}") from exc
