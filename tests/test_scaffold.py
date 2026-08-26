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
    assert "pyreact-framework>=1.1.0" in manifest.dependencies()
    assert manifest.requires_python == ">=3.10"
    assert manifest.scripts()["dev"] == "pyreact dev"
    assert manifest.scripts()["build"] == "pyreact build"
    assert (destination / "src/app.py").is_file()
    assert not (destination / "src/server.py").exists()
    assert not (destination / "src/build.py").exists()
    assert (destination / "src/components/dashboard.py").is_file()
    assert (destination / "public/styles.css").is_file()
    assert not (destination / "public/app.js").exists()
    assert (destination / "tests/test_app.py").is_file()
    assert (destination / "tests/test_runtime.py").is_file()
    assert "render_to_string" in (destination / "src/app.py").read_text(encoding="utf-8")
    assert "from pyreact import Link, Router" in (
        destination / "src/components/dashboard.py"
    ).read_text(encoding="utf-8")


def test_generated_python_is_valid_and_has_no_template_markers(tmp_path):
    destination = tmp_path / "syntax-check"
    create_project(destination, "Syntax Check")

    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        assert "{{PROJECT_NAME}}" not in content
        assert "{{PACKAGE_NAME}}" not in content
        if path.suffix == ".py":
            compile(content, str(path), "exec")


def test_create_project_refuses_non_empty_directory(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(PrpmError, match="não está vazio"):
        create_project(destination, "existing")


def test_create_project_refuses_existing_file_path(tmp_path):
    destination = tmp_path / "existing"
    destination.write_text("user data", encoding="utf-8")

    with pytest.raises(PrpmError, match="não é um diretório"):
        create_project(destination, "existing")

    assert destination.read_text(encoding="utf-8") == "user data"
