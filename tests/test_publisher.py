from pathlib import Path
from types import SimpleNamespace

from prpm import publisher
from prpm.release import ReleaseBundle, file_sha256
from prpm.repository import get_repository


def test_publish_keeps_token_out_of_command_line(tmp_path, monkeypatch):
    artifact = tmp_path / "demo-1.0.0.tar.gz"
    artifact.write_bytes(b"artifact")
    bundle = ReleaseBundle(
        directory=tmp_path,
        manifest_path=tmp_path / "prpm-manifest.json",
        signature_path=tmp_path / "prpm-manifest.sig",
        document={
            "name": "demo",
            "version": "1.0.0",
            "artifacts": [
                {
                    "filename": artifact.name,
                    "sha256": file_sha256(artifact),
                }
            ],
        },
        artifacts=(artifact,),
    )
    captured = {}

    monkeypatch.setattr(publisher, "build_release", lambda *args, **kwargs: bundle)
    monkeypatch.setattr(publisher, "verify_local", lambda path: {"scope": "release"})
    monkeypatch.setattr(publisher, "load_token", lambda repository: ("pypi-secret", "keyring"))
    monkeypatch.setattr(
        publisher,
        "_wait_for_release",
        lambda target, repository: {
            "scope": "repository",
            "name": "demo",
            "version": "1.0.0",
            "files": [
                {
                    "filename": artifact.name,
                    "sha256": file_sha256(artifact),
                }
            ],
        },
    )

    def run(command, cwd, env):
        captured["command"] = command
        captured["env"] = env.copy()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(publisher.subprocess, "run", run)
    manifest = SimpleNamespace(root=tmp_path)
    report = publisher.publish(manifest, get_repository("pypi"))

    assert report["published"]
    assert "pypi-secret" not in " ".join(captured["command"])
    assert captured["env"]["TWINE_PASSWORD"] == "pypi-secret"
