<div align="center">

# PRPM

The package manager for the PyReact ecosystem.

[![CI](https://github.com/wanbnn/prpm/actions/workflows/ci.yml/badge.svg)](https://github.com/wanbnn/prpm/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prpm?logo=pypi&logoColor=white)](https://pypi.org/project/prpm/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/wanbnn/prpm/blob/master/LICENSE)
[![Docs](https://readthedocs.org/projects/prpm/badge/?version=latest)](https://prpm.readthedocs.io/en/latest/)

Create projects, install isolated dependencies, lock versions, and run scripts
with a single tool.

</div>

## Why PRPM?

PyReact projects are Python projects. PRPM builds on that ecosystem instead of
creating an incompatible registry:

- it uses the standard `pyproject.toml` as its manifest;
- resolves packages from PyPI, including `pyreact-framework`;
- automatically creates an isolated `.venv`;
- generates a reproducible `prpm.lock`;
- provides a familiar experience for npm users;
- remains compatible with `pip`, build backends, and Python editors.

## Installation

PRPM requires Python 3.9 or newer.

### Quick install

The bundled installer sets up the published release from PyPI and verifies the
resulting `prpm` command:

```bash
# Linux, macOS, and Windows Subsystem for Linux
curl -fsSL https://raw.githubusercontent.com/wanbnn/prpm/main/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/wanbnn/prpm/main/install.ps1 | iex
```

Both installers accept the same flags. Install the development version from
GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/wanbnn/prpm/main/install.sh | bash -s -- --dev
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/wanbnn/prpm/main/install.ps1))) -Dev
```

### Manual install

Install the latest published release with pip:

```bash
python -m pip install prpm
```

Install the development version directly from GitHub:

```bash
python -m pip install git+https://github.com/wanbnn/prpm.git
```

Set up a local development checkout:

```bash
git clone https://github.com/wanbnn/prpm.git
cd prpm
python -m pip install -e ".[dev]"
```

## Quick start

Create and prepare a PyReact application:

```bash
prpm create my-app
cd my-app
prpm run dev
```

The command creates a complete server-driven dashboard, installs
`pyreact-framework` inside `.venv`, and writes the lockfile. The generated
project uses PyReact hooks, routing, SSR, isolated browser sessions, hot reload,
production launcher, light and dark themes, and runtime tests.

For an existing project:

```bash
git clone https://github.com/wanbnn/agenticflow.git
cd agenticflow
prpm install
prpm exec agentic-flow
```

PRPM reads the dependencies already declared in `[project].dependencies`.

## Commands

| Command | Description |
| --- | --- |
| `prpm create <name>` | Create and install a PyReact application |
| `prpm init [-y]` | Initialize a `pyproject.toml` |
| `prpm install` / `prpm i` | Resolve, install, and update `prpm.lock` |
| `prpm install --frozen` | Install exactly from the lockfile; ideal for CI |
| `prpm add <package>` | Install and save a dependency |
| `prpm add -D <package>` | Install and save a development dependency |
| `prpm remove <package>` | Remove a dependency |
| `prpm update [packages]` | Update all or selected dependencies |
| `prpm list [--all]` | List direct or all dependencies |
| `prpm run [script]` | List or run scripts |
| `prpm exec <command>` | Run a binary inside `.venv` |
| `prpm test` | Shortcut for the `test` script |
| `prpm info <package>` | Query package metadata on PyPI |
| `prpm lock [--check]` | Generate or validate the lockfile |
| `prpm login` / `logout` | Store or remove a token from the keyring |
| `prpm whoami` | Show the active credential and key |
| `prpm key <action>` | Generate, show, or rotate the Ed25519 key |
| `prpm pack` | Build, validate, and sign a wheel and sdist |
| `prpm publish` | Package and publish to PyPI |
| `prpm verify <target>` | Verify a local or published release |
| `prpm doctor` | Show the environment status |

Available aliases are `i`, `rm`, `up`, and `ls`.

### Dependencies

Dependency specifiers follow Python standards:

```bash
prpm add httpx
prpm add "fastapi>=0.115,<1"
prpm add -D "pytest>=8"
prpm add "component @ git+https://github.com/user/component.git"
```

When no version is supplied, PRPM saves the minimum resolved version, such as
`httpx>=0.28.1`.

### Scripts

Declare scripts in the manifest:

```toml
[tool.prpm.scripts]
dev = "pyreact dev"
build = "pyreact build"
test = "python -m pytest"
serve = ["python", "-m", "my_app"]
```

Run them without manually activating `.venv`:

```bash
prpm run build
prpm test -q
prpm exec python --version
```

## Manifest and lockfile

The manifest remains a valid `pyproject.toml`:

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["pyreact-framework>=1.1.0"]

[project.optional-dependencies]
dev = ["pytest>=8"]
```

Commit `prpm.lock` to version control. It records the exact version, source, and
index-provided hashes for every package. In CI, use:

```bash
prpm install --frozen
prpm test
```

Frozen mode fails before installation if the manifest and lockfile differ.

## Publishing packages

PRPM uses PyPI as its registry. Create a token at
<https://pypi.org/manage/account/token/> and sign in:

```bash
prpm login
prpm whoami
```

The token is entered without terminal echo and stored in the system keyring. It
is never written to the project or passed on the command line. The first login
also creates an Ed25519 identity:

```bash
prpm key show
prpm key rotate
```

Prepare and verify a release without publishing it:

```bash
prpm pack
prpm verify dist
```

The `dist/` directory will contain the wheel, source distribution,
`prpm-manifest.json`, and `prpm-manifest.sig`. The manifest records SHA-256
hashes, sizes, dependencies, and the public key; the signature authenticates
that manifest.

Publish with:

```bash
prpm publish
```

PRPM rebuilds the artifacts, runs `twine check`, validates the signature,
uploads the wheel and sdist, and compares remote hashes through the PyPI API.
Use `--no-build` for an already packed release or `--dry-run` to validate the
entire flow without uploading.

TestPyPI is also supported:

```bash
prpm login --repository testpypi
prpm publish --repository testpypi
```

For CI, provide `PRPM_PYPI_TOKEN` or `PRPM_TESTPYPI_TOKEN` as a secret
environment variable. When no keyring is available, `pack` creates an ephemeral
Ed25519 identity for that release.

Verify any published package:

```bash
prpm verify prpm
prpm verify "prpm==0.4.0"
```

Remote verification compares files with PyPI SHA-256 values and validates every
wheel `RECORD` entry. PyPI remains the authority for maintainer and package-name
ownership.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m prpm --help
```

See [CONTRIBUTING.md](https://github.com/wanbnn/prpm/blob/master/CONTRIBUTING.md)
for the contribution workflow and the
[complete documentation](https://prpm.readthedocs.io/en/latest/).

## License

MIT. See [LICENSE](https://github.com/wanbnn/prpm/blob/master/LICENSE).
