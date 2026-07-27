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
    assert manifest.scripts()["dev"] == "python -m src.server"
    assert manifest.scripts()["build"] == "python -m src.build"
    assert (destination / "src/app.py").is_file()
    assert (destination / "src/server.py").is_file()
    assert (destination / "src/components/dashboard.py").is_file()
    assert (destination / "public/styles.css").is_file()
    assert (destination / "public/app.js").is_file()
    assert (destination / "tests/test_app.py").is_file()
    assert (destination / "tests/test_server.py").is_file()
    assert "render_to_string" in (destination / "src/app.py").read_text(encoding="utf-8")
    assert "from pyreact import h" in (
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
