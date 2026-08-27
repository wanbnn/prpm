from types import SimpleNamespace

import pytest

from prpm.errors import PrpmError
from prpm.manager import PackageManager


class FakeManifest:
    def __init__(self, root):
        self.root = root
        self.requires_python = ">=3.10"

    def dependencies(self, dev=False):
        return ["pytest>=8"] if dev else ["app>=1", "worker>=2"]

    def all_dependencies(self, include_dev=True):
        values = self.dependencies(False)
        if include_dev:
            values.extend(self.dependencies(True))
        return values


def _manager(tmp_path):
    manager = PackageManager(FakeManifest(tmp_path))
    calls = []
    manager.environment.ensure = lambda: None
    manager.environment.satisfies_python = lambda _: True
    manager.environment.pip = (
        lambda args, **kwargs: calls.append(list(args)) or SimpleNamespace(stdout="")
    )
    return manager, calls


def test_selective_update_preserves_other_direct_pins_and_installs_new_lock(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: True
    retained = []

    def direct_pins(*, include_dev=True, exclude_names=None):
        retained.append((include_dev, exclude_names))
        return ["worker==2.4.0", "pytest==9.1.1"]

    manager.lockfile.direct_pins = direct_pins
    resolved = {"packages": [{"name": "app", "version": "1.8.0"}]}
    resolve_calls = []
    manager.lockfile.resolve = lambda *args, **kwargs: resolve_calls.append(
        (args, kwargs)
    ) or resolved
    written = []
    manager.lockfile.write = lambda document: written.append(document)
    manager.lockfile.pinned_requirements = lambda include_dev=True: [
        "app==1.8.0",
        "worker==2.4.0",
        "pytest==9.1.1",
    ]

    manager.update(["app"])

    assert retained == [(True, {"app"})]
    assert resolve_calls[0][1]["constraints"] == ["worker==2.4.0", "pytest==9.1.1"]
    assert written == [resolved]
    assert calls == [["install", "app==1.8.0", "worker==2.4.0", "pytest==9.1.1"]]


def test_selective_update_requires_current_lock_baseline(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: False

    with pytest.raises(PrpmError, match="lock atual"):
        manager.update(["app"])

    assert calls == []


def test_full_update_allows_every_direct_dependency_to_move(tmp_path):
    manager, calls = _manager(tmp_path)
    resolved = {"packages": []}
    resolve_calls = []
    manager.lockfile.resolve = lambda *args, **kwargs: resolve_calls.append(
        (args, kwargs)
    ) or resolved
    manager.lockfile.write = lambda document: None
    manager.lockfile.pinned_requirements = lambda include_dev=True: [
        "app==1.8.0",
        "worker==3.0.0",
        "pytest==9.1.1",
    ]

    manager.update([])

    assert resolve_calls[0][1]["constraints"] is None
    assert calls == [["install", "app==1.8.0", "worker==3.0.0", "pytest==9.1.1"]]


def test_production_update_keeps_dev_direct_dependency_pinned(tmp_path):
    manager, calls = _manager(tmp_path)
    manager.lockfile.is_current = lambda requirements: True
    requested = []
    manager.lockfile.direct_pins = lambda **kwargs: requested.append(kwargs) or [
        "pytest==9.1.1"
    ]
    manager.lockfile.resolve = lambda *args, **kwargs: {"packages": []}
    manager.lockfile.write = lambda document: None
    manager.lockfile.pinned_requirements = lambda include_dev=True: (
        ["app==1.8.0", "worker==3.0.0"] if not include_dev else []
    )

    manager.update([], include_dev=False)

    assert requested == [
        {
            "include_dev": True,
            "exclude_names": {"app", "worker"},
        }
    ]
    assert calls == [["install", "app==1.8.0", "worker==3.0.0"]]


def test_update_rejects_package_outside_selected_dependency_scope(tmp_path):
    manager, calls = _manager(tmp_path)

    with pytest.raises(PrpmError, match="Não encontrado no manifesto"):
        manager.update(["pytest"], include_dev=False)

    assert calls == []
