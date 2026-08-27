import hashlib

import pytest

from prpm.errors import PrpmError
from prpm.repository import REPOSITORIES
from prpm import verification


def _payload(files):
    return {
        "info": {"name": "demo", "version": "1.0.0"},
        "urls": files,
        "ownership": {},
    }


def test_remote_verification_releases_each_artifact_before_next_download(
    monkeypatch,
):
    contents = {
        "demo-1.0.0.tar.gz": b"first artifact",
        "demo-1.0.0.zip": b"second artifact",
        "demo-1.0.0-py3-none-any.whl.metadata": b"third artifact",
    }
    files = [
        {
            "filename": filename,
            "url": f"https://files.example/{filename}",
            "size": len(content),
            "digests": {"sha256": hashlib.sha256(content).hexdigest()},
        }
        for filename, content in contents.items()
    ]
    monkeypatch.setattr(verification, "_get_json", lambda url: _payload(files))

    resident_before_download = []

    def fake_download(url, destination):
        resident_before_download.append(
            sorted(path.name for path in destination.parent.iterdir())
        )
        content = contents[destination.name]
        destination.write_bytes(content)
        return hashlib.sha256(content).hexdigest(), len(content)

    monkeypatch.setattr(verification, "_download", fake_download)

    report = verification.verify_remote("demo==1.0.0", REPOSITORIES["pypi"])

    assert resident_before_download == [[], [], []]
    assert [item["filename"] for item in report["files"]] == list(contents)
    assert [item["size"] for item in report["files"]] == [
        len(content) for content in contents.values()
    ]


def test_remote_verification_uses_streamed_digest_without_rehashing(
    monkeypatch,
):
    content = b"verified while downloading"
    filename = "demo-1.0.0.tar.gz"
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(
        verification,
        "_get_json",
        lambda url: _payload(
            [
                {
                    "filename": filename,
                    "url": f"https://files.example/{filename}",
                    "size": len(content),
                    "digests": {"sha256": digest},
                }
            ]
        ),
    )

    def fake_download(url, destination):
        destination.write_bytes(content)
        return digest, len(content)

    monkeypatch.setattr(verification, "_download", fake_download)
    monkeypatch.setattr(
        verification,
        "file_sha256",
        lambda path: (_ for _ in ()).throw(AssertionError("unexpected second hash pass")),
    )

    report = verification.verify_remote("demo==1.0.0", REPOSITORIES["pypi"])

    assert report["files"] == [
        {"filename": filename, "sha256": digest, "size": len(content)}
    ]


def test_remote_verification_rejects_index_size_mismatch_and_cleans_artifact(
    monkeypatch,
):
    content = b"payload"
    filename = "demo-1.0.0.tar.gz"
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(
        verification,
        "_get_json",
        lambda url: _payload(
            [
                {
                    "filename": filename,
                    "url": f"https://files.example/{filename}",
                    "size": len(content) + 1,
                    "digests": {"sha256": digest},
                }
            ]
        ),
    )
    downloaded_paths = []

    def fake_download(url, destination):
        downloaded_paths.append(destination)
        destination.write_bytes(content)
        return digest, len(content)

    monkeypatch.setattr(verification, "_download", fake_download)

    with pytest.raises(PrpmError, match="Tamanho do artefato divergente"):
        verification.verify_remote("demo==1.0.0", REPOSITORIES["pypi"])

    assert downloaded_paths
    assert all(not path.exists() for path in downloaded_paths)
