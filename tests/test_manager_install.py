from pathlib import Path
from types import SimpleNamespace

from prpm.manager import PackageManager


class FakeManifest:
    def __init__(self, root):
        self.root = root
        self.requires_python = ">=3.9"

    def all_dependencies(self, include_dev=True):
        values = ["app>=1"]
        if include_dev:
            values.append("pytest>=8")
        return values

    def dependencies(self, dev=False):
        return ["pytest>=8"] if dev else ["app>=1"]


def _manager(tmp_path):
    manager = PackageManager(FakeManifest(tmp_path))
    calls = []
    manager.environment.ensure = lambda: None
    manager.environment.satisfies_python = lambda _: True
    manager.environment.pip = lambda args, **kwargs: calls.append(list(args)) or SimpleNamespace(stdout="")
    return manager, calls


def test_regular_install_uses_exact_versions_from_new_lock(tmp_path):
    manager, calls = _manager(tmp_path)
    resolved = {
        "lockVersion": 1,
        "contentHash": "sha256:test",
        "packages": [
            {"name": "app", "version": "1.4.2", "requirement": "app==1.4.2", "dev": False},
            {"name": "dep", "version": "3.1.0", "requirement": "dep==3.1.0", "dev": False},
            {"name": "pytest", "version": "9.1.1", "requirement": "pytest==9.1.1", "dev": True},
        ],
    }
    manager.lockfile.resolve = lambda *args, **kwargs: resolved
    written = []
    manager.lockfile.write = lambda document: written.append(document)
    manager.lockfile.pinned_requirements = lambda include_dev=True: (
        ["app==1.4.2", "dep==3.1.0", "pytest==9.1.1"]
        if include_dev
        else ["app==1.4.2", "dep==3.1.0"]
    )

    manager.install(include_dev=True)

    assert written == [resolved]
    assert calls == [["install", "app==1.4.2", "dep==3.1.0", "pytest==9.1.1"]]
    assert "app>=1" not in calls[0]
    assert "pytest>=8" not in calls[0]


def test_regular_production_install_filters_dev_from_lock(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.resolve = lambda *args, **kwargs: {"packages": []}
    manager.lockfile.write = lambda document: None
    requested_modes = []

    def pinned(include_dev=True):
        requested_modes.append(include_dev)
        return ["app==1.4.2", "dep==3.1.0"]

    manager.lockfile.pinned_requirements = pinned

    manager.install(include_dev=False)

    assert requested_modes == [False]
    assert calls == [["install", "app==1.4.2", "dep==3.1.0"]]


def test_frozen_and_regular_install_share_the_same_pinned_path(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: True
    manager.lockfile.pinned_requirements = lambda include_dev=True: ["app==1.4.2"]

    manager.install(frozen=True)

    assert calls == [["install", "app==1.4.2"]]


def test_verified_install_uses_pip_require_hashes_and_lockfile_lines(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: True
    manager.lockfile.hashed_requirements = lambda include_dev=True: [
        "app==1.4.2 --hash=sha256:" + "a" * 64,
        "dep==3.1.0 --hash=sha256:" + "b" * 64,
    ]

    manager.install(frozen=True, verify_hashes=True)

    assert len(calls) == 1
    assert calls[0][:3] == ["install", "--require-hashes", "-r"]
    requirements_path = Path(calls[0][3])
    # The temporary file is intentionally gone after pip returns; the important
    # contract is that pip received --require-hashes and a generated -r file.
    assert not requirements_path.exists()


def test_verified_install_can_be_enabled_by_environment(tmp_path, monkeypatch):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: True
    requested = []
    manager.lockfile.hashed_requirements = lambda include_dev=True: requested.append(include_dev) or [
        "app==1.4.2 --hash=sha256:" + "a" * 64
    ]
    monkeypatch.setenv("PRPM_VERIFY_HASHES", "1")

    manager.install(include_dev=False, frozen=True)

    assert requested == [False]
    assert calls[0][:3] == ["install", "--require-hashes", "-r"]
