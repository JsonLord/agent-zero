#!/usr/bin/env python3
"""Non-root Space lifecycle: private SearXNG plus the public Agent Zero UI."""

import json
import os
import secrets
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

SEARX_PYTHON = "/usr/local/searxng/searx-pyenv/bin/python"
SEARX_SOURCE = "/usr/local/searxng/searxng-src"
READY_URL = "http://127.0.0.1:55510/config"


def write_settings(path):
    # JSON is also valid YAML. Never mutate /etc or persistent user settings.
    settings = {
        "use_default_settings": {"engines": {"remove": ["radio browser", "wikidata"]}},
        "general": {"debug": False, "instance_name": "OpenOperator Search"},
        "server": {
            "secret_key": secrets.token_hex(32),
            "bind_address": "127.0.0.1",
            "port": 55510,
            "limiter": False,
            "image_proxy": False,
        },
        "search": {"formats": ["html", "json"]},
    }
    path.write_text(json.dumps(settings), encoding="utf-8")
    path.chmod(0o600)


def ready(url):
    # This fixed loopback probe must never be sent through an outbound proxy.
    try:
        with build_opener(ProxyHandler({})).open(url, timeout=1) as response:
            data = json.loads(response.read(1024 * 1024))
            return (
                response.status == 200
                and isinstance(data, dict)
                and isinstance(data.get("engines"), list)
            )
    except (OSError, ValueError):
        return False


def stop(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def serve(
    search_command,
    ui_command,
    *,
    env,
    cwd,
    ready_url=READY_URL,
    startup_timeout=30,
    restart_delay=5,
):
    stopping = False

    def request_stop(*_):
        nonlocal stopping
        stopping = True

    old_handlers = {
        sig: signal.signal(sig, request_stop) for sig in (signal.SIGTERM, signal.SIGINT)
    }
    search = ui = None
    next_start = 0
    deadline = time.monotonic() + startup_timeout
    checked = False
    try:
        while not stopping:
            now = time.monotonic()
            if search is not None and search.poll() is not None:
                print(
                    f"SearXNG exited ({search.returncode}); retrying in {restart_delay}s.",
                    flush=True,
                )
                stop(search)  # also clean up surviving worker processes
                search = None
                next_start = now + restart_delay
            if search is None and now >= next_start:
                try:
                    search = subprocess.Popen(
                        search_command, env=env, cwd=cwd, start_new_session=True
                    )
                    print("Starting private SearXNG at 127.0.0.1:55510.", flush=True)
                except OSError:
                    print(
                        "SearXNG could not start; check the image installation.",
                        flush=True,
                    )
                    next_start = now + restart_delay
            if not checked:
                if search is not None and search.poll() is None and ready(ready_url):
                    print(
                        "SearXNG ready: configuration endpoint returned engine registry.",
                        flush=True,
                    )
                    checked = True
                elif now >= deadline:
                    print(
                        "SearXNG readiness timed out; UI will use configured search fallbacks while startup retries.",
                        flush=True,
                    )
                    checked = True
            if checked and ui is None:
                ui = subprocess.Popen(ui_command, start_new_session=True)
            if ui is not None and ui.poll() is not None:
                return ui.returncode
            time.sleep(0.2)
        return 0
    finally:
        stop(ui)
        stop(search)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


def main():
    with tempfile.TemporaryDirectory(prefix="openoperator-searxng-") as directory:
        settings = Path(directory) / "settings.yml"
        write_settings(settings)
        env = dict(os.environ, SEARXNG_SETTINGS_PATH=str(settings))
        return serve(
            [
                SEARX_PYTHON,
                "-m",
                "gunicorn",
                "--bind",
                "127.0.0.1:55510",
                "--workers",
                "1",
                "--threads",
                "4",
                "--timeout",
                "60",
                "--access-logfile",
                "/dev/null",
                "searx.webapp:app",
            ],
            ["/opt/venv-a0/bin/python", "run_ui.py", "--dockerized=true"],
            env=env,
            cwd=SEARX_SOURCE,
        )


if __name__ == "__main__":
    raise SystemExit(main())
