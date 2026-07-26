import json

import pytest

from prpm.errors import PrpmError
from prpm.lockfile import LOCK_VERSION, Lockfile, content_hash


def test_lockfile_round_trip(tmp_path):
    lock = Lockfile(tmp_path)
    document = {
        "lockVersion": LOCK_VERSION,
        "contentHash": content_hash(["demo>=1"]),
        "packages": [{"name": "demo", "version": "1.2.3"}],
    }
    lock.write(document)

    assert lock.is_current(["demo>=1"])
    assert lock.pinned_requirements() == ["demo==1.2.3"]


def test_lockfile_can_omit_dev_packages(tmp_path):
    lock = Lockfile(tmp_path)
    lock.write(
        {
            "lockVersion": LOCK_VERSION,
            "contentHash": content_hash(["app", "pytest"]),
            "packages": [
                {"name": "app", "version": "1.0", "dev": False},
                {"name": "pytest", "version": "9.0", "dev": True},
            ],
        }
    )
    assert lock.pinned_requirements(include_dev=False) == ["app==1.0"]


def test_lockfile_rejects_unknown_version(tmp_path):
    (tmp_path / "prpm.lock").write_text(
        json.dumps({"lockVersion": 999}), encoding="utf-8"
    )
    with pytest.raises(PrpmError, match="não suportada"):
        Lockfile(tmp_path).read()
