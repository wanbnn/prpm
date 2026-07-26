from __future__ import annotations

from pathlib import Path

from prpm.errors import PrpmError
from prpm.manifest import normalized_project_name

PYPROJECT = """[project]
name = "{package_name}"
version = "0.1.0"
description = "Aplicação criada com PyReact e PRPM"
requires-python = ">=3.9"
dependencies = [
    "pyreact-framework>=1.0.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.pyreact]
entry = "src/index.py"
output = "dist"
dev_port = 3000
ssr = true
css_modules = true
source_maps = true

[tool.prpm.scripts]
dev = "pyreact dev"
build = "pyreact build"
test = "python -m pytest"
generate = "pyreact generate"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

INDEX = '''"""Entrada principal da aplicação PyReact."""

from pyreact import h, use_state


def App(props):
    count, set_count = use_state(0)
    return h(
        "main",
        {"className": "app"},
        h("h1", None, "Olá, PyReact!"),
        h("p", None, "Este projeto usa PRPM para gerenciar suas dependências."),
        h(
            "div",
            {"className": "counter"},
            h("span", None, f"Contador: {count}"),
            h("button", {"onClick": lambda _: set_count(count + 1)}, "+"),
            h("button", {"onClick": lambda _: set_count(count - 1)}, "−"),
        ),
    )
'''

HTML = """<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
      body {{ font: 16px system-ui; margin: 0; background: #0f1020; color: #f5f5ff; }}
      .app {{ width: min(680px, 90%); margin: 15vh auto; text-align: center; }}
      .counter {{ display: flex; gap: 12px; justify-content: center; align-items: center; }}
      button {{ padding: 8px 16px; cursor: pointer; }}
    </style>
  </head>
  <body><div id="root"></div></body>
</html>
"""

TEST = """from pyreact import h
from pyreact.testing import cleanup, render
from src.index import App


def test_app_renders():
    result = render(h(App, {}))
    assert result.get_by_text("Olá, PyReact!")
    cleanup()
"""

README = """# {title}

Aplicação PyReact gerenciada com [PRPM](https://github.com/wanbnn/prpm).

```bash
prpm install
prpm run dev
```

Comandos disponíveis:

- `prpm run dev`: servidor de desenvolvimento;
- `prpm run build`: build de produção;
- `prpm test`: testes;
- `prpm add pacote`: adiciona uma dependência.
"""

GITIGNORE = """.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
dist/
"""


def create_project(destination: Path, name: str) -> None:
    if destination.exists() and any(destination.iterdir()):
        raise PrpmError(f"O diretório {destination} já existe e não está vazio.")
    destination.mkdir(parents=True, exist_ok=True)
    for directory in ("src/components", "src/hooks", "src/pages", "public", "tests"):
        (destination / directory).mkdir(parents=True, exist_ok=True)
    package_name = normalized_project_name(name)
    files = {
        "pyproject.toml": PYPROJECT.format(package_name=package_name),
        "src/__init__.py": '"""Aplicação PyReact."""\n',
        "src/index.py": INDEX,
        "src/components/__init__.py": "",
        "src/hooks/__init__.py": "",
        "src/pages/__init__.py": "",
        "public/index.html": HTML.format(title=name),
        "tests/test_app.py": TEST,
        "README.md": README.format(title=name),
        ".gitignore": GITIGNORE,
    }
    for relative, content in files.items():
        (destination / relative).write_text(content, encoding="utf-8")

