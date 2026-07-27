import pytest

from prpm import auth
from prpm.errors import PrpmError
from prpm.repository import get_repository


def fake_keyring(monkeypatch):
    values = {}
    monkeypatch.setattr(
        auth.keyring, "set_password", lambda service, user, value: values.__setitem__((service, user), value)
    )
    monkeypatch.setattr(
        auth.keyring, "get_password", lambda service, user: values.get((service, user))
    )
    monkeypatch.setattr(
        auth.keyring, "delete_password", lambda service, user: values.pop((service, user))
    )
    return values


def test_token_round_trip_uses_keyring(monkeypatch):
    fake_keyring(monkeypatch)
    repository = get_repository("pypi")
    auth.save_token(repository, "pypi-example")

    token, source = auth.load_token(repository)
    assert token == "pypi-example"
    assert source == "keyring"
    assert auth.delete_token(repository)


def test_environment_token_takes_precedence(monkeypatch):
    fake_keyring(monkeypatch)
    repository = get_repository("pypi")
    auth.save_token(repository, "pypi-stored")
    monkeypatch.setenv("PRPM_PYPI_TOKEN", "pypi-environment")

    assert auth.load_token(repository) == ("pypi-environment", "env:PRPM_PYPI_TOKEN")


def test_rejects_non_pypi_token():
    with pytest.raises(PrpmError, match="começam"):
        auth.validate_token("not-a-token")

