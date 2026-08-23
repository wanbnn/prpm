"""Tests for the GitHub Actions release-version helper."""

from pathlib import Path

import pytest

from scripts.set_ci_version import create_post_version, update_ci_version


def test_create_post_version_is_unique_per_attempt():
    assert create_post_version("0.4.0", 12345, 1) == "0.4.0.post1234501"
    assert create_post_version("0.4.0", 12345, 2) == "0.4.0.post1234502"


@pytest.mark.parametrize("base_version", ["0.4.0.post1", "v0.4.0", "0.4-beta"])
def test_create_post_version_rejects_non_release_versions(base_version):
    with pytest.raises(ValueError):
        create_post_version(base_version, 1, 1)


def test_update_ci_version_updates_build_and_runtime_files(tmp_path: Path):
    package = tmp_path / "src" / "prpm"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "2.4.0"\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text(
        '__version__ = "2.4.0"\n',
        encoding="utf-8",
    )

    version = update_ci_version(tmp_path, run_id=42, run_attempt=3)

    assert version == "2.4.0.post4203"
    assert 'version = "2.4.0.post4203"' in (
        tmp_path / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert '__version__ = "2.4.0.post4203"' in (
        package / "__init__.py"
    ).read_text(encoding="utf-8")
