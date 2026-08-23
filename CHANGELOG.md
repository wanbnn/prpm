# Changelog

All notable changes to this project will be documented in this file.

## 0.4.0 - 2026-08-23

### Added

- Generated applications now demonstrate PyReact hooks, keyed lists, routing,
  SSR, session state, and the live runtime protocol.
- Runtime-level scaffold tests for events, forms, state updates, and routes.

### Changed

- Migrated generated development and production commands to `pyreact dev` and
  `pyreact build`.
- Removed the duplicated HTTP server, JSON fragment API, browser JavaScript,
  and static-only builder from the scaffold.
- Raised the Python requirement to 3.10 and the generated PyReact requirement
  to 1.1.0.

## 0.3.0 - 2026-07-27

- Added `prpm login`, `logout`, and `whoami` with system-keyring token storage.
- Added locally generated Ed25519 identities and key rotation with `prpm key`.
- Added `prpm pack` to build, validate, and sign releases.
- Added `prpm publish` for secure publishing to PyPI and TestPyPI.
- Added `prpm verify` to validate manifests, PyPI hashes, and wheel `RECORD`
  entries.
- Added CI credentials through `PRPM_PYPI_TOKEN` and `PRPM_TESTPYPI_TOKEN`.

## 0.2.1 - 2026-07-27

- Published PRPM on PyPI.
- Updated the recommended installation command to `python -m pip install prpm`.
- Modernized package license metadata.

## 0.2.0 - 2026-07-27

- Replaced the empty `prpm create` page with a functional dashboard.
- Added real PyReact components and server-side rendering to the boilerplate.
- Added a development server, fragment API, and static build.
- Added filtering, completion, task creation, and light/dark themes.
- Expanded the generated project with components, data, assets, and six tests.

## 0.1.0 - 2026-07-26

- Initial CLI with `init`, `create`, `install`, `add`, `remove`, `update`,
  `list`, `run`, `exec`, `test`, `info`, `lock`, and `doctor`.
- Isolated `.venv` environments per project.
- Integration with `pyproject.toml`, PyPI, and pip's resolver.
- Reproducible lockfile with versions, URLs, and hashes.
- Ready-to-use scaffold for PyReact applications.
