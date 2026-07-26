import pytest

from prpm.cli import build_parser, dispatch
from prpm.errors import PrpmError
from prpm.manifest import Manifest


def call(arguments):
    parser = build_parser()
    return dispatch(parser.parse_args(arguments), parser)


def test_init_creates_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert call(["init", "example", "-y"]) == 0
    assert Manifest(tmp_path).name == "example"


def test_run_lists_scripts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    call(["init", "example", "-y"])
    assert call(["run"]) == 0
    assert "test" in capsys.readouterr().out


def test_exec_requires_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    call(["init", "example", "-y"])
    with pytest.raises(PrpmError, match="Informe um comando"):
        call(["exec"])

