from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dispatch = _load(
    "spynel_dispatch_test",
    "agents/spynel/skills/spynel-dispatch/scripts/spynel_dispatch.py",
)
paperclip = _load(
    "paperclip_api_test",
    "agents/spynel/skills/paperclip-board-manager/scripts/paperclip_api.py",
)


@pytest.mark.parametrize(
    ("text", "profile", "sdk", "message"),
    [
        ("do this", None, None, "do this"),
        ("@researcher do this", "researcher", None, "do this"),
        ("/hermes do this", None, "hermes", "do this"),
        ("@researcher /hermes do this", "researcher", "hermes", "do this"),
    ],
)
def test_route_syntax(text, profile, sdk, message):
    route = dispatch.parse_route(text)
    assert (route.profile, route.sdk, route.message) == (profile, sdk, message)


def test_sdk_requires_registered_https_endpoint(monkeypatch):
    route = dispatch.parse_route("/hermes work")
    monkeypatch.delenv("SPYNEL_SDK_HERMES_URL", raising=False)
    with pytest.raises(KeyError, match="SPYNEL_SDK_HERMES_URL"):
        dispatch.resolve_external(route)
    monkeypatch.setenv("SPYNEL_SDK_HERMES_URL", "http://gateway.example/api")
    with pytest.raises(ValueError, match="HTTPS"):
        dispatch.resolve_external(route)


def test_registered_profile_precedes_internal(monkeypatch):
    monkeypatch.setenv("SPYNEL_AGENT_RESEARCHER_URL", "https://example.test/run")
    assert dispatch.resolve_external(dispatch.parse_route("@researcher work"))[0] == "https://example.test/run"


def test_user_embedded_url_cannot_override_registered_destination(monkeypatch):
    monkeypatch.setenv("SPYNEL_SDK_HERMES_URL", "https://gateway.example/run")
    route = dispatch.parse_route("/hermes send https://attacker.example/steal")
    assert dispatch.resolve_external(route)[0] == "https://gateway.example/run"
    assert route.message == "send https://attacker.example/steal"


def test_local_route_never_dispatches():
    result = asyncio.run(dispatch.dispatch("local work", timeout=1, poll_interval=.25))
    assert result["mode"] == "local"


def test_internal_unknown_profile_fails_explicitly(monkeypatch):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "secret")

    async def fake(*args, **kwargs):
        return 404, {"error": "Agent profile not found"}, ""

    monkeypatch.setattr(dispatch, "_curl_json", fake)
    result = asyncio.run(dispatch.dispatch("@missing task", timeout=1, poll_interval=.25))
    assert result["mode"] == "internal"
    assert result["ok"] is False
    assert "Unknown" in result["error"]


def test_internal_delegation_polls_to_result(monkeypatch):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "secret")
    replies = iter([
        (200, {"context_id": "fresh", "status": "running"}, ""),
        (200, {"context_id": "fresh", "status": "running", "log_from": 2, "log_progress": "thinking"}, ""),
        (200, {"context_id": "fresh", "status": "completed", "log_from": 3, "result": "done"}, ""),
    ])

    async def fake(*args, **kwargs):
        return next(replies)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(dispatch, "_curl_json", fake)
    monkeypatch.setattr(dispatch.asyncio, "sleep", no_sleep)
    result = asyncio.run(dispatch.dispatch("@researcher task", timeout=2, poll_interval=.25))
    assert result["ok"] is True
    assert result["context_id"] == "fresh"
    assert result["response"] == "done"
    assert any(event["state"] == "polling" for event in result["events"])


def test_external_poll_timeout(monkeypatch):
    monkeypatch.setenv("SPYNEL_SDK_HERMES_URL", "https://example.test/run")

    async def post(*args, **kwargs):
        return 202, {"status": "running", "poll_url": "https://example.test/status"}, ""

    async def get(*args, **kwargs):
        return 200, {"status": "running"}, ""

    async def no_sleep(_):
        return None

    times = iter([0, 2, 2])
    monkeypatch.setattr(dispatch, "_curl_json", post)
    monkeypatch.setattr(dispatch, "_curl_get", get)
    monkeypatch.setattr(dispatch.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(dispatch.asyncio, "get_running_loop", lambda: SimpleNamespace(time=lambda: next(times)))
    result = asyncio.run(dispatch.dispatch("/hermes task", timeout=1, poll_interval=.25))
    assert result["state"] == "timeout"


def test_external_malformed_json_fails(monkeypatch):
    monkeypatch.setenv("SPYNEL_SDK_HERMES_URL", "https://example.test/run")

    async def post(*args, **kwargs):
        return 200, {"malformed_json": True, "text": "not-json"}, ""

    monkeypatch.setattr(dispatch, "_curl_json", post)
    result = asyncio.run(dispatch.dispatch("/hermes task", timeout=1, poll_interval=.25))
    assert result["ok"] is False
    assert result["state"] == "failed"
    assert "malformed JSON" in result["error"]


def test_external_request_timeout_is_structured(monkeypatch):
    monkeypatch.setenv("SPYNEL_SDK_HERMES_URL", "https://example.test/run")

    async def post(*args, **kwargs):
        raise TimeoutError("request timed out")

    monkeypatch.setattr(dispatch, "_curl_json", post)
    result = asyncio.run(dispatch.dispatch("/hermes task", timeout=1, poll_interval=.25))
    assert result["ok"] is False
    assert result["state"] == "timeout"
    assert result["events"][-1]["state"] == "timeout"


def test_curl_uses_argv_and_kills_after_timeout(monkeypatch):
    calls = []

    class Proc:
        stdin = stdout = stderr = object()
        def __init__(self): self.waits = 0
        async def communicate(self, body): await asyncio.Future()
        def terminate(self): calls.append("terminate")
        def kill(self): calls.append("kill")
        async def wait(self):
            self.waits += 1
            if "kill" not in calls:
                await asyncio.Future()

    async def create(*argv, **kwargs):
        calls.append(argv)
        return Proc()

    async def immediate_wait(awaitable, timeout):
        awaitable.close() if hasattr(awaitable, "close") else None
        raise asyncio.TimeoutError

    monkeypatch.setattr(dispatch.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(dispatch.asyncio, "wait_for", immediate_wait)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(dispatch._curl_json("https://example.test", {"x": "$(bad)"}, 1))
    assert "curl" in calls[0] and "$(bad)" not in calls[0]
    assert calls[-2:] == ["terminate", "kill"]


def test_profile_creation_api_is_protected_and_path_safe():
    source = (ROOT / "api/agent_profile_create.py").read_text()
    assert "class CreateAgentProfile(ApiHandler)" in source
    assert "subagents.save_agent_data(name, profile)" in source
    assert 'name.lower() in _RESERVED' in source
    assert '"/" in key_s' in source and '"\\\\" in key_s' in source
    # The endpoint intentionally keeps ApiHandler's authenticated + CSRF defaults.
    assert "requires_auth" not in source and "requires_csrf" not in source


def test_paperclip_restricts_base_and_path(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_BASE_URL", "http://example.test")
    with pytest.raises(SystemExit, match="HTTPS"):
        paperclip.base_url()
    with pytest.raises(SystemExit, match="/api/"):
        paperclip.safe_path("/admin")
    with pytest.raises(SystemExit):
        paperclip.safe_path("/api/../secret")


def test_paperclip_curl_does_not_use_shell(monkeypatch, capsys):
    seen = {}
    monkeypatch.setenv("PAPERCLIP_BASE_URL", "https://paperclip.example")
    monkeypatch.setenv("PAPERCLIP_API_TOKEN", "token")

    def run(argv, **kwargs):
        seen.update(argv=argv, kwargs=kwargs)
        return SimpleNamespace(stdout=b'{"ok":true}', stderr=b"", returncode=0)

    monkeypatch.setattr(paperclip.subprocess, "run", run)
    assert paperclip.request("POST", "/api/issues", {"title": "$(bad)"}) == 0
    assert "shell" not in seen["kwargs"]
    assert "$(bad)" not in seen["argv"]


def test_huggingface_image_is_non_root_and_direct_startup():
    dockerfile = (ROOT / "Dockerfile").read_text()
    entrypoint = (ROOT / "docker/run/fs/exe/huggingface-entrypoint.sh").read_text()
    assert "WEB_UI_HOST=0.0.0.0" in dockerfile and "WEB_UI_PORT=7860" in dockerfile
    assert "USER 1000:1000" in dockerfile
    assert "PIP_NO_INDEX=1" in dockerfile
    assert "spacy download en_core_web_sm" in dockerfile
    assert "/exe/initialize.sh" not in entrypoint
    assert "run_ui.py" in entrypoint
    assert "chpasswd" not in entrypoint
    assert 'settings["mcp_server_token"] = api_key' in entrypoint


def test_colab_cli_has_lifecycle_commands():
    script = (ROOT / "scripts/colab_a0.py").read_text()
    assert 'choices=("start", "health", "stop")' in script
    assert 'default="0.0.0.0"' in script
    assert "default=7860" in script
    assert 'fields[2] == "Z"' in script
    assert 'b"run_ui.py" not in command' in script
