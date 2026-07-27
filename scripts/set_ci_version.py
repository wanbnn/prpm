"""Generate a unique PEP 440 post-release version for CI publication."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PROJECT_VERSION = re.compile(r'(?m)^(version\s*=\s*")[^"]+(")\s*$')
PACKAGE_VERSION = re.compile(
    r"(?m)^(__version__\s*=\s*)(?P<quote>['\"])[^'\"]+(?P=quote)\s*$"
)
BASE_VERSION = re.compile(r"^\d+(?:\.\d+)*$")


def create_post_version(base_version: str, run_id: int, run_attempt: int) -> str:
    """Build a unique and monotonically increasing PEP 440 post-release."""
    if not BASE_VERSION.fullmatch(base_version):
        raise ValueError(
            f"Base version must contain numeric release segments only: {base_version!r}"
        )
    if run_id < 1 or not 1 <= run_attempt <= 99:
        raise ValueError("run_id must be positive and run_attempt must be between 1 and 99")

    return f"{base_version}.post{run_id * 100 + run_attempt}"


def _read_base_version(pyproject: Path) -> str:
    content = pyproject.read_text(encoding="utf-8")
    match = PROJECT_VERSION.search(content)
    if not match:
        raise ValueError(f"Unable to find project version in {pyproject}")
    return match.group(0).split('"')[1]


def _replace_project_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = PROJECT_VERSION.subn(
        rf"\g<1>{version}\g<2>", content, count=1
    )
    if count != 1:
        raise ValueError(f"Unable to update exactly one version in {path}")
    path.write_text(updated, encoding="utf-8")


def _replace_package_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")

    def replacement(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return f"{match.group(1)}{quote}{version}{quote}"

    updated, count = PACKAGE_VERSION.subn(replacement, content, count=1)
    if count != 1:
        raise ValueError(f"Unable to update exactly one version in {path}")
    path.write_text(updated, encoding="utf-8")


def update_ci_version(root: Path, run_id: int, run_attempt: int) -> str:
    """Update build metadata and the runtime version."""
    pyproject = root / "pyproject.toml"
    package_init = root / "src" / "prpm" / "__init__.py"
    version = create_post_version(
        _read_base_version(pyproject), run_id=run_id, run_attempt=run_attempt
    )
    _replace_project_version(pyproject, version)
    _replace_package_version(package_init, version)
    return version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    print(update_ci_version(args.root.resolve(), args.run_id, args.run_attempt))


if __name__ == "__main__":
    main()
