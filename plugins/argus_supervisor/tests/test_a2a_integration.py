"""Real loopback HTTP JSON-RPC transport; no external service or model keys."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from plugins.argus_supervisor.helpers.a2a_client import OpenTrainingA2AClient
from plugins.argus_supervisor.helpers.heartbeat import Supervisor
from plugins.argus_supervisor.helpers.models import SupervisorError


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["completed", "failed", "input-required"])
async def test_submit_poll_terminal_recovery_over_http(setup, terminal):
    s, remote, argus = setup
    observed_headers = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.reply(asyncio.run(remote.transport("GET", self.path, None)))

        def do_POST(self):
            observed_headers.append(self.headers.get("Authorization"))
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.reply(asyncio.run(remote.transport("POST", "", payload)))

        def reply(self, result):
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = OpenTrainingA2AClient("https://test.example/a2a", token="test-key")
        # Production constructor refuses HTTP. Test alone substitutes a loopback
        # transport address to exercise actual aiohttp without external TLS/DNS.
        client.url = f"http://127.0.0.1:{server.server_port}"
        s.client = client
        await s.discover()
        c = s.store.load("campaign-1")
        c.remote_task_id = None
        await s.mutation(c, "claim_control", {}, None)
        await s.mutation(
            c, "submit", {"text": "Harmless fixture task"}, c.controller_epoch
        )
        await s.tick()
        remote.task["status"]["state"] = terminal
        remote.task["metadata"]["argus_supervisor"]["revision"] = "2"
        await s.tick()
        count = len(argus.calls)
        restarted = Supervisor(s.store, client, argus)
        await restarted.tick()
        assert len(argus.calls) == count
        assert s.store.load(c.campaign_id).remote_state == terminal
        assert len([x for x in remote.calls if x[0] == "message/send"]) == 1
        assert observed_headers and all(
            h == "Bearer test-key" for h in observed_headers
        )
        # Remote takes over: persisted local lease must no longer permit mutation.
        remote.lease["epoch"] += 1
        await restarted.tick()
        c = s.store.load(c.campaign_id)
        assert c.mode == "observer"
        with pytest.raises(SupervisorError):
            await restarted.mutation(c, "cancel", {"id": "task-1"}, c.controller_epoch)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
