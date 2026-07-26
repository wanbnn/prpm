from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Sequence

from prpm.console import console
from prpm.errors import PrpmError


class ProjectEnvironment:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / ".venv"

    @property
    def python(self) -> Path:
        if os.name == "nt":
            return self.path / "Scripts" / "python.exe"
        return self.path / "bin" / "python"

    @property
    def bin_dir(self) -> Path:
        return self.python.parent

    def ensure(self) -> None:
        if self.python.is_file():
            return
        console.info(f"Criando ambiente virtual em {self.path.name}")
        try:
            venv.EnvBuilder(with_pip=True).create(self.path)
        except Exception as exc:
            raise PrpmError(f"Não foi possível criar a .venv: {exc}") from exc

    def pip(
        self,
        arguments: Sequence[str],
        *,
        capture: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.ensure()
        command = [str(self.python), "-m", "pip", *arguments]
        try:
            return subprocess.run(
                command,
                cwd=self.root,
                check=check,
                text=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise PrpmError(detail or f"pip terminou com código {exc.returncode}.") from exc

    def installed(self) -> dict[str, str]:
        result = self.pip(["list", "--format=json"], capture=True)
        return {
            item["name"]: item["version"]
            for item in json.loads(result.stdout)
            if item["name"].lower() not in {"pip", "setuptools", "wheel"}
        }

    def run(self, command: Sequence[str]) -> int:
        self.ensure()
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(self.path)
        env["PATH"] = os.pathsep.join([str(self.bin_dir), env.get("PATH", "")])
        try:
            return subprocess.run(list(command), cwd=self.root, env=env).returncode
        except FileNotFoundError as exc:
            raise PrpmError(f"Comando não encontrado: {command[0]}") from exc

    def satisfies_python(self, specifier: str) -> bool:
        if not specifier:
            return True
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version

        return Version(".".join(map(str, sys.version_info[:3]))) in SpecifierSet(specifier)

