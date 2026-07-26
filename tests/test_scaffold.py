from pathlib import Path

import pytest

from prpm.errors import PrpmError
from prpm.manifest import Manifest
from prpm.scaffold import create_project


def test_create_project_builds_pyreact_layout(tmp_path):
    destination = tmp_path / "Minha App"
    create_project(destination, "Minha App")

    manifest = Manifest(destination)
    assert manifest.name == "minha-app"
    assert "pyreact-framework>=1.0.5" in manifest.dependencies()
    assert manifest.scripts()["dev"] == "pyreact dev"
    assert (destination / "src/index.py").is_file()
    assert (destination / "tests/test_app.py").is_file()


def test_create_project_refuses_non_empty_directory(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(PrpmError, match="não está vazio"):
        create_project(destination, "existing")

