#!/usr/bin/env python3
"""Small lifecycle CLI for Agent Zero smoke tests in Google Colab."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import urlopen


def _paths(state_dir: Path) -> tuple[Path, Path]:
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "agent-zero.pid", state_dir / "agent-zero.log"


def _pid(path: Path) -> int | None:
    try:
        value = int(path.read_text().strip())
        os.kill(value, 0)
        proc = Path(f"/proc/{value}")
        if proc.exists():
            fields = (proc / "stat").read_text().split()
            if len(fields) > 2 and fields[2] == "Z":
                return None
            command = (proc / "cmdline").read_bytes().replace(b"\0", b" ")
            if b"run_ui.py" not in command:
                return None
        return value
    except (FileNotFoundError, PermissionError, ValueError, ProcessLookupError):
        return None


def health(url: str, timeout: float) -> bool:
    try:
        with urlopen(url.rstrip("/") + "/api/health", timeout=timeout) as response:
            return 200 <= response.status < 300
    except OSError:
        return False


def start(root: Path, state_dir: Path, host: str, port: int, wait: float) -> int:
    pid_path, log_path = _paths(state_dir)
    if running := _pid(pid_path):
        print(json.dumps({"status": "running", "pid": running}))
        return 0
    log = log_path.open("ab")
    env = {**os.environ, "WEB_UI_HOST": host, "WEB_UI_PORT": str(port)}
    process = subprocess.Popen(
        [sys.executable, "run_ui.py"], cwd=root, env=env, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True,
    )
    log.close()
    pid_path.write_text(str(process.pid))
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(json.dumps({"status": "failed", "pid": process.pid, "log": str(log_path)}))
            return 1
        if health(url, 2):
            print(json.dumps({"status": "healthy", "pid": process.pid, "url": url}))
            return 0
        time.sleep(0.5)
    print(json.dumps({"status": "starting", "pid": process.pid, "url": url, "log": str(log_path)}))
    return 2


def stop(state_dir: Path, wait: float) -> int:
    pid_path, _ = _paths(state_dir)
    running = _pid(pid_path)
    if running is None:
        pid_path.unlink(missing_ok=True)
        print(json.dumps({"status": "stopped"}))
        return 0
    os.killpg(running, signal.SIGTERM)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if _pid(pid_path) is None:
            pid_path.unlink(missing_ok=True)
            print(json.dumps({"status": "stopped", "pid": running}))
            return 0
        time.sleep(0.25)
    os.killpg(running, signal.SIGKILL)
    pid_path.unlink(missing_ok=True)
    print(json.dumps({"status": "killed", "pid": running}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "health", "stop"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state-dir", type=Path, default=Path("/content/.agent-zero"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--wait", type=float, default=60)
    args = parser.parse_args()
    if args.action == "start":
        return start(args.root, args.state_dir, args.host, args.port, args.wait)
    if args.action == "stop":
        return stop(args.state_dir, args.wait)
    ok = health(f"http://127.0.0.1:{args.port}", min(args.wait, 10))
    print(json.dumps({"status": "healthy" if ok else "unhealthy", "port": args.port}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
