"""Read-only in-container release acceptance. Never claims or submits work."""

import asyncio
import json
import os
import time
from pathlib import Path

import aiohttp

from helpers import plugins, subagents
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.argus_bridge import ArgusBridge
from plugins.argus_supervisor.helpers.foreman_bridge import ForemanBridge
from plugins.argus_supervisor.helpers.models import SupervisorError


def public_tcp_ports():
    ports = set()
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        if not Path(path).exists():
            continue
        for line in Path(path).read_text().splitlines()[1:]:
            fields = line.split()
            address, port = fields[1].split(":")
            if fields[3] != "0A":
                continue
            if address in {"0100007F", "00000000000000000000000001000000"}:
                continue
            ports.add(int(port, 16))
    return sorted(ports)


async def checks():
    root = Path(os.getenv("ARGUS_SUPERVISOR_STATE_ROOT", "/a0/usr/argus-supervisor"))
    report = {
        "uid_1000": os.getuid() == 1000,
        "profile_discoverable": "argus-supervisor"
        in subagents.get_available_agents_dict(None),
        "plugin_loaded": "argus_supervisor" in plugins.get_enabled_plugins(None),
        "public_tcp_ports": public_tcp_ports(),
        "token_present": bool(os.getenv("OPENTRAINING_A2A_TOKEN")),
    }
    report["only_existing_public_port"] = set(report["public_tcp_ports"]) == {7860}
    for name, bridge in (
        ("argus", ArgusBridge(root / "argus-home")),
        ("foreman", ForemanBridge(root / "foreman-home")),
    ):
        try:
            report[name + "_runtime"] = await bridge.verify()
        except SupervisorError as error:
            report[name + "_runtime"] = {"error": str(error)}
    expected = os.getenv("ARGUS_EXPECTED_SOURCE_SHA", "")
    try:
        sha = json.loads(Path("/a0/openoperator-build.json").read_text())["source_sha"]
    except (OSError, ValueError, KeyError):
        sha = None
    try:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
            session.get(
                "http://127.0.0.1:7860/health", allow_redirects=False
            ) as response,
        ):
            data = json.loads(await response.content.read(16384))
            report["health_sha"] = data.get("sha") if response.status == 200 else None
    except (aiohttp.ClientError, OSError, ValueError):
        report["health_sha"] = None
    report["health_sha_match"] = bool(expected and report["health_sha"] == expected)
    report["build_sha"] = sha
    report["expected_sha_match"] = bool(expected and sha == expected)
    try:
        supervisor = service.get()
        report["capabilities"] = await supervisor.discover()
        # A separate smoke process cannot inspect the serving process singleton.
        # Observe its durable heartbeat receipt instead of fabricating health.
        try:
            receipt = json.loads((root / "state/supervisor.json").read_text())
            report["heartbeat_last_tick"] = receipt["last_tick"]
            report["heartbeat_healthy"] = time.time() - receipt["last_tick"] < 360
        except (OSError, ValueError, KeyError):
            report["heartbeat_healthy"] = False
    except SupervisorError as error:
        report["supervisor_error"] = str(error)
    return report


if __name__ == "__main__":
    result = asyncio.run(checks())
    print(json.dumps(result, indent=2))
    required = (
        "uid_1000",
        "profile_discoverable",
        "plugin_loaded",
        "only_existing_public_port",
        "expected_sha_match",
        "health_sha_match",
        "heartbeat_healthy",
    )
    good = all(result.get(key) is True for key in required)
    good = good and not any(
        result.get(key, {}).get("error") for key in ("argus_runtime", "foreman_runtime")
    )
    good = good and bool(result.get("capabilities", {}).get("discover"))
    raise SystemExit(0 if good else 1)
