"""Finite subprocess RPC; isolated runtimes receive no A2A credentials."""

import asyncio
import atexit
import json
import os
import signal
import threading
from pathlib import Path

from .models import SupervisorError
from .security import clean

_active = set()
_process_lock = threading.Lock()


def cleanup():
    with _process_lock:
        for pid in _active:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


atexit.register(cleanup)

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"


async def invoke(python, worker, payload, home, *, timeout=120, kind="argus"):
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "PATH",
            "LANG",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "REQUESTS_CA_BUNDLE",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "no_proxy",
        }
        or (
            kind == "argus"
            and (
                key.startswith("ARGUS_SKILL_")
                or key
                in {
                    "OPENAI_API_KEY",
                    "OPENAI_BASE_URL",
                    "ANTHROPIC_API_KEY",
                    "CODEX_HOME",
                }
            )
        )
        or (kind == "foreman" and key.startswith("TYPESAFE_"))
    }
    env.update(
        HOME=str(home),
        XDG_CACHE_HOME=str(home / ".cache"),
        ARGUS_SKILL_HOME=str(home),
        FOREMAN_DATA_DIR=str(home / "foreman"),
        PIP_NO_INDEX="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    env["ARGUS_SKILL_MAX_ROUNDS"] = "2"
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            python,
            str(RUNTIME / worker),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=home,
            env=env,
            start_new_session=True,
        )
        with _process_lock:
            _active.add(process.pid)
        output, _ = await asyncio.wait_for(
            process.communicate(json.dumps(clean(payload, 24000)).encode()), timeout
        )
        if process.returncode != 0 or len(output) > 65536:
            raise SupervisorError(kind + "_runtime_failed")
        result = json.loads(output)
        if not isinstance(result, dict) or result.get("error"):
            raise SupervisorError(kind + "_runtime_unavailable")
        return clean(result, 24000)
    except (OSError, ValueError):
        raise SupervisorError(kind + "_runtime_unavailable") from None
    except TimeoutError:
        raise SupervisorError(kind + "_runtime_timeout") from None
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
            with _process_lock:
                _active.discard(process.pid)
