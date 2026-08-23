import os
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from prpm.scaffold import create_project


pyreact = pytest.importorskip("pyreact")
playwright = pytest.importorskip("playwright.sync_api")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"PyReact stopped early:\n{stdout}\n{stderr}")
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise TimeoutError(f"PyReact did not start at {url}")


def test_generated_project_uses_current_pyreact_runtime(tmp_path):
    project = tmp_path / "live-app"
    create_project(project, "Live App")
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}

    generated_tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert generated_tests.returncode == 0, generated_tests.stderr

    production_build = subprocess.run(
        [sys.executable, "-m", "pyreact.cli.main", "build"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert production_build.returncode == 0, production_build.stderr
    assert (project / "dist" / "serve.py").is_file()
    assert (project / "dist" / "src" / "app.py").is_file()

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [sys.executable, "-m", "pyreact.cli.main", "dev", "--port", str(port), "--no-open"],
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until_ready(url, process)
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle")
                assert page.title() == "Live App · Orbit"
                playwright.expect(page.locator(".task")).to_have_count(4)
                assert page.locator("style[data-pyreact-styles]").count() == 1

                page.locator("input[name=title]").fill("Validate the live runtime")
                page.get_by_role("button", name="Add").click()
                playwright.expect(page.get_by_text("Validate the live runtime")).to_be_visible()
                playwright.expect(page.locator(".task")).to_have_count(5)

                page.get_by_role("link", name="About").click()
                playwright.expect(page.get_by_text("Python is the runtime")).to_be_visible()
                assert page.url.endswith("/about")
            finally:
                browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
