from __future__ import annotations

from dataclasses import dataclass

from prpm.errors import PrpmError


@dataclass(frozen=True)
class Repository:
    name: str
    upload_url: str
    json_url: str
    token_env: str


REPOSITORIES = {
    "pypi": Repository(
        name="pypi",
        upload_url="https://upload.pypi.org/legacy/",
        json_url="https://pypi.org/pypi",
        token_env="PRPM_PYPI_TOKEN",
    ),
    "testpypi": Repository(
        name="testpypi",
        upload_url="https://test.pypi.org/legacy/",
        json_url="https://test.pypi.org/pypi",
        token_env="PRPM_TESTPYPI_TOKEN",
    ),
}


def get_repository(name: str) -> Repository:
    try:
        return REPOSITORIES[name.lower()]
    except KeyError as exc:
        available = ", ".join(sorted(REPOSITORIES))
        raise PrpmError(f"Repositório desconhecido: {name}. Use: {available}.") from exc

