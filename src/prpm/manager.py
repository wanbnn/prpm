from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

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

    def install(
        self,
        include_dev: bool = True,
        frozen: bool = False,
        verify_hashes: Optional[bool] = None,
    ) -> None:
        all_requirements = self.manifest.all_dependencies(True)
        if verify_hashes is None:
            verify_hashes = os.getenv("PRPM_VERIFY_HASHES", "").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
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
        else:
            console.info("Resolvendo dependências")
            document = self.lockfile.resolve(
                self.environment,
                all_requirements,
                self.manifest.all_dependencies(True),
                self.manifest.dependencies(False),
            )
            self.lockfile.write(document)

        if verify_hashes:
            selected = self.lockfile.hashed_requirements(include_dev)
            if selected:
                console.info(
                    f"Instalando {len(selected)} pacote(s) com hashes do lockfile"
                )
                with tempfile.TemporaryDirectory(prefix="prpm-install-") as temporary:
                    requirements_file = Path(temporary) / "requirements.txt"
                    requirements_file.write_text(
                        "\n".join(selected) + "\n",
                        encoding="utf-8",
                    )
                    self.environment.pip(
                        [
                            "install",
                            "--require-hashes",
                            "-r",
                            str(requirements_file),
                        ]
                    )
        else:
            # The lockfile is authoritative for both regular and frozen installs.
            # Installing the manifest ranges after resolving them would run pip's
            # resolver a second time and could produce a different environment from
            # the lockfile if the package index changed between both operations.
            selected = self.lockfile.pinned_requirements(include_dev)
            if selected:
                console.info(f"Instalando {len(selected)} pacote(s) do lockfile")
                self.environment.pip(["install", *selected])
        console.success("Dependências instaladas")

    def sync(
        self,
        include_dev: bool = True,
        verify_hashes: Optional[bool] = None,
    ) -> list[str]:
        """Make the project virtualenv match the current lockfile exactly.

        Desired packages are installed first. Only after installation succeeds
        are packages absent from the selected lock scope removed, so a failed
        install never destroys the previously working environment. The project
        itself is protected when it has been installed editable into its own
        virtualenv.
        """
        all_requirements = self.manifest.all_dependencies(True)
        if not self.lockfile.is_current(all_requirements):
            raise PrpmError(
                "Sincronização exige um prpm.lock atual; execute `prpm install` primeiro."
            )

        self.install(
            include_dev=include_dev,
            frozen=True,
            verify_hashes=verify_hashes,
        )

        selected = self.lockfile.pinned_requirements(include_dev)
        desired = {
            canonicalize_name(Requirement(requirement).name)
            for requirement in selected
        }
        protected = {canonicalize_name(self.manifest.name)}
        installed = self.environment.installed()
        extras = sorted(
            (
                name
                for name in installed
                if canonicalize_name(name) not in desired | protected
            ),
            key=str.lower,
        )
        if extras:
            console.info(
                f"Removendo {len(extras)} pacote(s) ausente(s) do lockfile"
            )
            self.environment.pip(["uninstall", "-y", *extras])
        console.success(
            "Ambiente sincronizado com o lockfile"
            + (f"; {len(extras)} pacote(s) removido(s)" if extras else "")
        )
        return extras

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
        all_requirements = self.manifest.all_dependencies(True)
        updatable = self.manifest.all_dependencies(include_dev)
        updatable_by_name = {
            canonicalize_name(Requirement(item).name): item for item in updatable
        }

        if packages:
            targets = {canonicalize_name(Requirement(item).name) for item in packages}
            missing = sorted(targets - set(updatable_by_name))
            if missing:
                raise PrpmError(
                    "Não encontrado no manifesto: " + ", ".join(missing)
                )
        else:
            targets = set(updatable_by_name)

        # A partial update needs the current lock as its baseline. Direct
        # dependencies outside the requested target set remain constrained to
        # their locked versions; shared transitives are still free to move when
        # the selected package requires it.
        partial = bool(packages) or not include_dev
        constraints: list[str] | None = None
        if partial:
            if not self.lockfile.is_current(all_requirements):
                raise PrpmError(
                    "Atualização seletiva exige um prpm.lock atual; execute `prpm install` primeiro."
                )
            constraints = self.lockfile.direct_pins(
                include_dev=True,
                exclude_names=targets,
            )

        if not self.environment.satisfies_python(self.manifest.requires_python):
            raise PrpmError(
                f"Python atual não satisfaz {self.manifest.requires_python}."
            )
        self.environment.ensure()
        console.info("Resolvendo atualização")
        document = self.lockfile.resolve(
            self.environment,
            all_requirements,
            self.manifest.all_dependencies(True),
            self.manifest.dependencies(False),
            constraints=constraints,
        )
        self.lockfile.write(document)

        # Reconcile the environment from the exact graph just written. This
        # keeps .venv and prpm.lock synchronized instead of installing one graph
        # and independently resolving another graph afterward.
        selected = self.lockfile.pinned_requirements(include_dev)
        if selected:
            console.info(f"Instalando {len(selected)} pacote(s) atualizados do lockfile")
            self.environment.pip(["install", *selected])
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
