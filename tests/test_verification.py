import base64
import csv
import hashlib
import io
import json
import zipfile

import pytest

from prpm.errors import PrpmError
from prpm.release import MANIFEST_FILE, SIGNATURE_FILE, file_sha256, load_release
from prpm.signing import canonical_json, public_key_text
from prpm.verification import verify_wheel


def make_wheel(path):
    files = {
        "demo/__init__.py": b'__version__ = "1.0.0"\n',
        "demo-1.0.0.dist-info/METADATA": b"Name: demo\nVersion: 1.0.0\n",
        "demo-1.0.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
    }
    record_name = "demo-1.0.0.dist-info/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for name, content in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        writer.writerow([name, f"sha256={digest}", len(content)])
    writer.writerow([record_name, "", ""])
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr(record_name, output.getvalue())


def test_verify_wheel_checks_every_record_entry(tmp_path):
    wheel = tmp_path / "demo-1.0.0-py3-none-any.whl"
    make_wheel(wheel)
    assert verify_wheel(wheel)["recordEntries"] == 3


def test_verify_wheel_rejects_tampered_content(tmp_path):
    wheel = tmp_path / "demo-1.0.0-py3-none-any.whl"
    make_wheel(wheel)
    with zipfile.ZipFile(wheel) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    entries["demo/__init__.py"] = b"tampered"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    with pytest.raises(PrpmError, match="divergente"):
        verify_wheel(wheel)


def test_load_release_verifies_manifest_signature(tmp_path, monkeypatch):
    from prpm import signing

    values = {}
    monkeypatch.setattr(
        signing.keyring,
        "set_password",
        lambda service, user, value: values.__setitem__((service, user), value),
    )
    monkeypatch.setattr(
        signing.keyring,
        "get_password",
        lambda service, user: values.get((service, user)),
    )
    identity = signing.generate_identity()
    artifact = tmp_path / "demo-1.0.0.tar.gz"
    artifact.write_bytes(b"release")
    document = {
        "schemaVersion": 1,
        "name": "demo",
        "version": "1.0.0",
        "signing": {
            "algorithm": "ed25519",
            "keyId": identity.key_id,
            "publicKey": public_key_text(identity),
        },
        "artifacts": [
            {
                "filename": artifact.name,
                "size": artifact.stat().st_size,
                "sha256": file_sha256(artifact),
                "type": "sdist",
            }
        ],
    }
    signature = {
        "schemaVersion": 1,
        "algorithm": "ed25519",
        "keyId": identity.key_id,
        "signature": identity.sign(canonical_json(document)),
    }
    (tmp_path / MANIFEST_FILE).write_text(json.dumps(document), encoding="utf-8")
    (tmp_path / SIGNATURE_FILE).write_text(json.dumps(signature), encoding="utf-8")

    assert load_release(tmp_path).document["name"] == "demo"
