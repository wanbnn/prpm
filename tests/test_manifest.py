from pathlib import Path

from prpm.lockfile import content_hash
from prpm.manifest import Manifest, make_manifest


def project(tmp_path: Path) -> Manifest:
    (tmp_path / "pyproject.toml").write_text(make_manifest("demo"), encoding="utf-8")
    return Manifest(tmp_path)


def test_manifest_add_replaces_same_normalized_package(tmp_path):
    manifest = project(tmp_path)
    manifest.add("Requests>=2")
    manifest.add("requests==2.32.0")
    manifest.save()

    loaded = Manifest(tmp_path)
    assert loaded.dependencies() == ["requests==2.32.0"]


def test_manifest_keeps_dev_dependencies_separate(tmp_path):
    manifest = project(tmp_path)
    manifest.add("pytest>=8", dev=True)
    manifest.save()

    loaded = Manifest(tmp_path)
    assert loaded.dependencies() == []
    assert loaded.dependencies(dev=True) == ["pytest>=8"]


def test_manifest_remove_searches_both_groups(tmp_path):
    manifest = project(tmp_path)
    manifest.add("httpx>=0.27")
    manifest.add("pytest>=8", dev=True)
    assert manifest.remove("HTTPX")
    assert manifest.remove("pytest")
    assert manifest.all_dependencies() == []


def test_content_hash_is_order_independent():
    assert content_hash(["b>=1", "a>=1"]) == content_hash(["a>=1", "b>=1"])

