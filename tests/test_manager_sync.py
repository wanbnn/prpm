from types import SimpleNamespace

import pytest

from prpm.cli import build_parser
from prpm.errors import PrpmError
from prpm.manager import PackageManager


class FakeManifest:
    def __init__(self, root):
        self.root = root
        self.name = "demo-project"
        self.requires_python = ">=3.10"

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
    manager.environment.pip = (
        lambda args, **kwargs: calls.append(list(args)) or SimpleNamespace(stdout="")
    )
    manager.lockfile.is_current = lambda requirements: True
    manager.lockfile.pinned_requirements = lambda include_dev=True: (
        ["app==1.4.2", "dep==3.1.0", "pytest==9.1.1"]
        if include_dev
        else ["app==1.4.2", "dep==3.1.0"]
    )
    return manager, calls


def test_sync_installs_locked_graph_before_removing_extras(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.environment.installed = lambda: {
        "app": "1.4.2",
        "dep": "3.1.0",
        "pytest": "9.1.1",
        "orphan": "2.0.0",
        "demo-project": "0.1.0",
    }

    removed = manager.sync()

    assert removed == ["orphan"]
    assert calls == [
        ["install", "app==1.4.2", "dep==3.1.0", "pytest==9.1.1"],
        ["uninstall", "-y", "orphan"],
    ]


def test_sync_production_removes_dev_and_unlocked_packages(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.environment.installed = lambda: {
        "app": "1.4.2",
        "dep": "3.1.0",
        "pytest": "9.1.1",
        "debug-toolbar": "5.0.0",
    }

    removed = manager.sync(include_dev=False)

    assert removed == ["debug-toolbar", "pytest"]
    assert calls == [
        ["install", "app==1.4.2", "dep==3.1.0"],
        ["uninstall", "-y", "debug-toolbar", "pytest"],
    ]


def test_sync_does_not_mutate_environment_when_lock_is_stale(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: False
    manager.environment.installed = lambda: {"orphan": "2.0.0"}

    with pytest.raises(PrpmError, match="prpm.lock atual"):
        manager.sync()

    assert calls == []


def test_sync_command_is_registered_with_production_mode():
    parser = build_parser()

    args = parser.parse_args(["sync", "--production"])

    assert args.command == "sync"
    assert args.production is True
