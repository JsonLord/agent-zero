"""Exercise the Space process lifecycle with real local child processes."""

import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docker/run/fs/exe/huggingface-services.py"
spec = importlib.util.spec_from_file_location("space_services", SCRIPT)
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)


def test_private_runtime_settings(tmp_path):
    path = tmp_path / "settings.yml"
    services.write_settings(path)
    settings = json.loads(path.read_text())
    assert settings["server"]["bind_address"] == "127.0.0.1"
    assert settings["server"]["port"] == 55510
    assert settings["server"]["limiter"] is False
    assert "json" in settings["search"]["formats"]
    assert path.stat().st_mode & 0o777 == 0o600
    secret = settings["server"]["secret_key"]
    services.write_settings(path)
    assert json.loads(path.read_text())["server"]["secret_key"] != secret


def wait_for(predicate):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    pytest.fail("Space child lifecycle did not reach the expected state")


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@pytest.mark.parametrize("fail_first", [False, True])
def test_readiness_restart_and_sigterm_stop_both_children(tmp_path, fail_first):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    search_pid = tmp_path / "search.pid"
    ui_pid = tmp_path / "ui.pid"
    attempt = tmp_path / "attempt"
    child = tmp_path / "search.py"
    child.write_text(f"""
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
attempt = Path({str(attempt)!r})
if {fail_first!r} and not attempt.exists():
    attempt.touch()
    raise SystemExit(2)
Path({str(search_pid)!r}).write_text(str(os.getpid()))
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{{"engines": []}}')
    def log_message(self, *args): pass
HTTPServer(('127.0.0.1', {port}), Handler).serve_forever()
""")
    ui = [
        sys.executable,
        "-c",
        f"import os,time; from pathlib import Path; Path({str(ui_pid)!r}).write_text(str(os.getpid())); time.sleep(60)",
    ]
    runner = """import importlib.util,json,os,sys
spec=importlib.util.spec_from_file_location('services',sys.argv[1])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
raise SystemExit(m.serve(**json.loads(sys.argv[2]),env=os.environ.copy()))
"""
    params = {
        "search_command": [sys.executable, str(child)],
        "ui_command": ui,
        "cwd": str(tmp_path),
        "ready_url": f"http://127.0.0.1:{port}/config",
        "startup_timeout": 3,
        "restart_delay": 0.1,
    }
    with (tmp_path / "log").open("w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", runner, str(SCRIPT), json.dumps(params)],
            stdout=log,
            stderr=log,
        )
        try:
            wait_for(ui_pid.exists)
            assert search_pid.exists() and process.poll() is None
            first = int(search_pid.read_text())
            os.kill(first, signal.SIGTERM)
            wait_for(lambda: int(search_pid.read_text()) != first)
            second = int(search_pid.read_text())
            assert alive(second)
            process.terminate()
            assert process.wait(timeout=8) == 0
            assert not alive(second) and not alive(int(ui_pid.read_text()))
            log.seek(0)
            assert "SearXNG ready" in log.read()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=8)


def test_unavailable_service_still_runs_ui_and_returns_its_exit_code(tmp_path):
    assert (
        services.serve(
            [str(tmp_path / "missing")],
            [sys.executable, "-c", "raise SystemExit(7)"],
            env=os.environ.copy(),
            cwd=str(tmp_path),
            startup_timeout=0,
        )
        == 7
    )


def test_image_verifies_service_and_space_entrypoint_runs_lifecycle():
    image = (ROOT / "Dockerfile").read_text()
    entrypoint = (ROOT / "docker/run/fs/exe/huggingface-entrypoint.sh").read_text()
    assert (
        "searx-pyenv/bin/python -m pip install --no-cache-dir gunicorn==23.0.0" in image
    )
    assert "import searx, gunicorn" in image
    assert "exec /opt/venv-a0/bin/python /exe/huggingface-services.py" in entrypoint
    assert '"127.0.0.1:55510"' in SCRIPT.read_text()
