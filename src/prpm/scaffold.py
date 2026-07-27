from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from prpm.errors import PrpmError
from prpm.manifest import normalized_project_name

TEMPLATE_ROOT = "templates/pyreact_app"
TEMPLATE_FILES = (
    ("gitignore.tmpl", ".gitignore"),
    ("README.md.tmpl", "README.md"),
    ("pyproject.toml.tmpl", "pyproject.toml"),
    ("src/__init__.py.tmpl", "src/__init__.py"),
    ("src/app.py.tmpl", "src/app.py"),
    ("src/build.py.tmpl", "src/build.py"),
    ("src/data.py.tmpl", "src/data.py"),
    ("src/server.py.tmpl", "src/server.py"),
    ("src/components/__init__.py.tmpl", "src/components/__init__.py"),
    ("src/components/dashboard.py.tmpl", "src/components/dashboard.py"),
    ("public/app.js.tmpl", "public/app.js"),
    ("public/favicon.svg.tmpl", "public/favicon.svg"),
    ("public/styles.css.tmpl", "public/styles.css"),
    ("tests/test_app.py.tmpl", "tests/test_app.py"),
    ("tests/test_server.py.tmpl", "tests/test_server.py"),
)


def create_project(destination: Path, name: str) -> None:
    """Materialize the bundled PyReact application template."""
    if destination.exists() and any(destination.iterdir()):
        raise PrpmError(f"O diretório {destination} já existe e não está vazio.")

    destination.mkdir(parents=True, exist_ok=True)
    package_name = normalized_project_name(name)
    display_name = _display_name(name)
    template_root = files("prpm").joinpath(TEMPLATE_ROOT)
    replacements = {
        "{{PROJECT_NAME}}": display_name,
        "{{PACKAGE_NAME}}": package_name,
    }

    for template_name, output_name in TEMPLATE_FILES:
        resource = template_root.joinpath(template_name)
        try:
            content = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            raise PrpmError(f"Template interno ausente: {template_name}") from exc
        for marker, value in replacements.items():
            content = content.replace(marker, value)
        output = destination / output_name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")


def _display_name(value: str) -> str:
    raw = Path(value).name.replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in raw.split()) or "PyReact App"
