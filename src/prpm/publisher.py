from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from prpm.auth import load_token
from prpm.errors import PrpmError
from prpm.manifest import Manifest
from prpm.release import ReleaseBundle, build_release, load_release
from prpm.repository import Repository
from prpm.verification import verify_local, verify_remote


def publish(
    manifest: Manifest,
    repository: Repository,
    *,
    directory: Path | None = None,
    build: bool = True,
    skip_existing: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    release_directory = (directory or manifest.root / "dist").resolve()
    bundle = (
        build_release(manifest, release_directory, force=True)
        if build
        else load_release(release_directory)
    )
    local_report = verify_local(release_directory)
    if dry_run:
        return {
            "published": False,
            "dryRun": True,
            "local": local_report,
        }
    token, credential_source = load_token(repository)
    command = [
        sys.executable,
        "-m",
        "twine",
        "upload",
        "--non-interactive",
        "--repository-url",
        repository.upload_url,
    ]
    if skip_existing:
        command.append("--skip-existing")
    command.extend(map(str, bundle.artifacts))
    environment = os.environ.copy()
    environment["TWINE_USERNAME"] = "__token__"
    environment["TWINE_PASSWORD"] = token
    environment["TWINE_NON_INTERACTIVE"] = "1"
    result = subprocess.run(command, cwd=manifest.root, env=environment)
    token = ""
    environment["TWINE_PASSWORD"] = ""
    if result.returncode:
        raise PrpmError(f"Falha ao publicar (twine retornou {result.returncode}).")
    target = f"{bundle.document['name']}=={bundle.document['version']}"
    remote_report = _wait_for_release(target, repository)
    _compare_release(bundle, remote_report)
    return {
        "published": True,
        "repository": repository.name,
        "credentialSource": credential_source,
        "local": local_report,
        "remote": remote_report,
    }


def _wait_for_release(target: str, repository: Repository) -> dict[str, Any]:
    last_error: PrpmError | None = None
    for _ in range(10):
        try:
            return verify_remote(target, repository)
        except PrpmError as exc:
            last_error = exc
            time.sleep(1)
    raise PrpmError(
        f"Upload concluído, mas a validação remota ainda não está disponível: {last_error}"
    )


def _compare_release(
    bundle: ReleaseBundle, remote_report: dict[str, Any]
) -> None:
    local = {
        item["filename"]: item["sha256"]
        for item in bundle.document.get("artifacts", [])
    }
    remote = {
        item["filename"]: item["sha256"]
        for item in remote_report.get("files", [])
    }
    if local != remote:
        raise PrpmError(
            "Os hashes publicados não correspondem exatamente à release local."
        )
