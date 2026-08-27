import json

import pytest

from prpm.errors import PrpmError
from prpm.lockfile import (
    LOCK_VERSION,
    Lockfile,
    content_hash,
    resolution_environment,
)


def _document(requirements, packages):
    return {
        "lockVersion": LOCK_VERSION,
        "contentHash": content_hash(requirements),
        "environment": resolution_environment(),
        "packages": packages,
    }


def test_lockfile_round_trip(tmp_path):
    lock = Lockfile(tmp_path)
    document = _document(
        ["demo>=1"],
        [{"name": "demo", "version": "1.2.3"}],
    )
    lock.write(document)

    assert lock.is_current(["demo>=1"])
    assert lock.pinned_requirements() == ["demo==1.2.3"]


def test_lockfile_is_not_current_when_resolution_environment_changes(tmp_path, monkeypatch):
    lock = Lockfile(tmp_path)
    document = _document(
        ["demo>=1"],
        [{"name": "demo", "version": "1.2.3"}],
    )
    lock.write(document)

    changed = dict(document["environment"])
    changed["sys_platform"] = "different-platform"
    monkeypatch.setattr("prpm.lockfile.resolution_environment", lambda: changed)

    assert not lock.is_current(["demo>=1"])


def test_legacy_lock_without_environment_requires_regeneration(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        {
            "lockVersion": LOCK_VERSION,
            "contentHash": content_hash(["demo>=1"]),
            "python": "3.12.0",
            "packages": [{"name": "demo", "version": "1.2.3"}],
        }
    )

    assert not lock.is_current(["demo>=1"])


def test_generated_document_captures_marker_environment(tmp_path):
    document = Lockfile._document([], [])

    assert document["environment"] == resolution_environment()
    assert document["environment"]["python_version"]
    assert document["environment"]["sys_platform"]
    assert document["environment"]["platform_machine"] is not None


def test_lockfile_can_omit_dev_packages(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        _document(
            ["app", "pytest"],
            [
                {"name": "app", "version": "1.0", "dev": False},
                {"name": "pytest", "version": "9.0", "dev": True},
            ],
        )
    )
    assert lock.pinned_requirements(include_dev=False) == ["app==1.0"]


def test_direct_pins_keep_non_target_direct_dependencies_only(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        _document(
            ["app", "worker", "pytest"],
            [
                {"name": "app", "version": "1.5", "direct": True, "dev": False},
                {"name": "worker", "version": "2.4", "direct": True, "dev": False},
                {"name": "shared", "version": "4.0", "direct": False, "dev": False},
                {"name": "pytest", "version": "9.1", "direct": True, "dev": True},
            ],
        )
    )

    assert lock.direct_pins(exclude_names={"APP"}) == [
        "worker==2.4",
        "pytest==9.1",
    ]
    assert lock.direct_pins(include_dev=False, exclude_names={"app"}) == [
        "worker==2.4"
    ]


def test_hashed_requirements_support_new_and_legacy_sha256_values(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        _document(
            ["app", "pytest"],
            [
                {
                    "name": "app",
                    "version": "1.0",
                    "dev": False,
                    "hashes": ["sha256:" + "a" * 64],
                },
                {
                    "name": "pytest",
                    "version": "9.0",
                    "dev": True,
                    "hashes": ["b" * 64],
                },
            ],
        )
    )

    assert lock.hashed_requirements() == [
        "app==1.0 --hash=sha256:" + "a" * 64,
        "pytest==9.0 --hash=sha256:" + "b" * 64,
    ]
    assert lock.hashed_requirements(include_dev=False) == [
        "app==1.0 --hash=sha256:" + "a" * 64
    ]


def test_hashed_requirements_reject_missing_hashes_before_pip(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        _document(
            ["app"],
            [{"name": "app", "version": "1.0", "hashes": []}],
        )
    )

    with pytest.raises(PrpmError, match="hash para todos os pacotes"):
        lock.hashed_requirements()


def test_lockfile_rejects_unknown_version(tmp_path):
    (tmp_path / "prpm.lock").write_text(
        json.dumps({"lockVersion": 999}), encoding="utf-8"
    )
    with pytest.raises(PrpmError, match="não suportada"):
        Lockfile(tmp_path).read()
