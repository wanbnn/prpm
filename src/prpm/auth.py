from __future__ import annotations

import os

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from prpm.errors import PrpmError
from prpm.repository import Repository

TOKEN_USERNAME = "__token__"


def credential_service(repository: Repository) -> str:
    return f"prpm:{repository.upload_url}"


def validate_token(token: str) -> str:
    value = token.strip()
    if not value:
        raise PrpmError("O token do PyPI não pode ficar vazio.")
    if not value.startswith("pypi-"):
        raise PrpmError("Token inválido: tokens do PyPI começam com `pypi-`.")
    return value


def save_token(repository: Repository, token: str) -> None:
    value = validate_token(token)
    try:
        keyring.set_password(credential_service(repository), TOKEN_USERNAME, value)
    except KeyringError as exc:
        raise PrpmError(
            "O keyring do sistema não está disponível. "
            f"Use a variável {repository.token_env} nesta sessão."
        ) from exc


def load_token(repository: Repository) -> tuple[str, str]:
    environment_value = os.getenv(repository.token_env)
    if environment_value:
        return validate_token(environment_value), f"env:{repository.token_env}"
    try:
        stored = keyring.get_password(credential_service(repository), TOKEN_USERNAME)
    except KeyringError as exc:
        raise PrpmError(
            "Não foi possível acessar o keyring do sistema. "
            f"Defina {repository.token_env} ou execute `prpm login`."
        ) from exc
    if not stored:
        raise PrpmError(
            f"Nenhuma credencial para {repository.name}. Execute `prpm login "
            f"--repository {repository.name}`."
        )
    return validate_token(stored), "keyring"


def has_token(repository: Repository) -> tuple[bool, str | None]:
    try:
        _, source = load_token(repository)
    except PrpmError:
        return False, None
    return True, source


def delete_token(repository: Repository) -> bool:
    try:
        existing = keyring.get_password(credential_service(repository), TOKEN_USERNAME)
        if not existing:
            return False
        keyring.delete_password(credential_service(repository), TOKEN_USERNAME)
        return True
    except PasswordDeleteError:
        return False
    except KeyringError as exc:
        raise PrpmError("Não foi possível remover a credencial do keyring.") from exc

