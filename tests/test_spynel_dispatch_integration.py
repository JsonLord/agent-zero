"""Real curl -> authenticated API -> AgentContext worker -> response tool -> poll.

Only model boundaries and unrelated lifecycle hooks are controlled; no Space or
external provider is contacted and no production credentials are used.
"""

import importlib.util
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, request
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spynel_dispatch_integration",
    ROOT / "agents/spynel/skills/spynel-dispatch/scripts/spynel_dispatch.py",
)
dispatch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dispatch
spec.loader.exec_module(dispatch)


@pytest.fixture
def worker_api(monkeypatch, tmp_path):
    from agent import Agent, AgentConfig, AgentContext
    from api.api_message import ApiMessage
    from api.api_poll import ApiPoll
    from helpers import extension, settings
    from helpers.api import requires_api_key
    from helpers.llm_result import LLMResult
    from plugins._goal.tools import goal

    original_ids = {context.id for context in AgentContext.all()}
    config = {
        **settings.get_default_settings(),
        "mcp_server_token": "integration-only-token",
    }
    monkeypatch.setattr(settings, "get_settings", lambda *args, **kwargs: config)
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "integration-only-token")
    monkeypatch.delenv("SPYNEL_PROJECT", raising=False)
    monkeypatch.delenv("SPYNEL_WORKSPACE_ALIASES", raising=False)
    monkeypatch.setattr(extension, "call_extensions_sync", lambda *args, **kwargs: None)

    async def no_hooks(*args, **kwargs):
        pass

    monkeypatch.setattr(extension, "call_extensions_async", no_hooks)
    monkeypatch.setattr(goal, "_goals_directory", lambda: tmp_path / "goals")
    owned_configs = []

    def initialize_worker(override_settings):
        worker_config = AgentConfig(
            mcp_servers="", profile=override_settings["agent_profile"]
        )
        owned_configs.append(worker_config)
        return worker_config

    monkeypatch.setattr("api.api_message.initialize_agent", initialize_worker)

    async def prompt(self, **kwargs):
        return []

    received = []

    async def model(self, **kwargs):
        if not any(self.config is config for config in owned_configs):
            return LLMResult(response="Unrelated test worker completed")
        received.append(
            (
                self.config.profile,
                self.last_user_message.content["user_message"],
                self.context.id,
            )
        )
        return LLMResult(response="Executed by " + self.config.profile)

    async def intervention(self, *args, **kwargs):
        pass

    monkeypatch.setattr(Agent, "prepare_prompt", prompt)
    monkeypatch.setattr(Agent, "call_chat_model_turn", model)
    monkeypatch.setattr(Agent, "handle_intervention", intervention)
    app = Flask("spynel_dispatch_integration")
    lock = threading.Lock()
    for path, handler_class in [
        ("/api/api_message", ApiMessage),
        ("/api/api_poll", ApiPoll),
    ]:

        async def endpoint(handler_class=handler_class):
            return await handler_class(app, lock).handle_request(request)

        app.add_url_rule(path, path, requires_api_key(endpoint), methods=["POST"])
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_URL", base)
    root = tmp_path / "workdir"
    (root / "nodepad/src").mkdir(parents=True)
    (root / "nodepad/src/app.py").write_text('print("test")\n')
    (root / "notepad").symlink_to(root / "nodepad", target_is_directory=True)
    yield SimpleNamespace(root=root, received=received, base=base)
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    for context in AgentContext.all():
        if context.id not in original_ids:
            AgentContext.remove(context.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,options,profile,relative",
    [
        ("Have the reviewer inspect nodepad", {}, "reviewer", "nodepad"),
        (
            "@developer\nFix nodepad/src/app.py\n\n```python\nx = 1\n```",
            {},
            "developer",
            "nodepad/src",
        ),
        (
            "@developer\n    Fix nodepad/src/app.py\n    preserve this indentation\n",
            {},
            "developer",
            "nodepad/src",
        ),
        (
            "Please repair the parser\n\n    preserve indentation",
            {"profile": "developer", "workspace": "notepad"},
            "developer",
            "nodepad",
        ),
    ],
)
async def test_actual_worker_receives_profile_original_task_and_canonical_workspace(
    worker_api, message, options, profile, relative
):
    result = await dispatch.dispatch(
        message,
        timeout=10,
        poll_interval=0.25,
        workspace_root=worker_api.root,
        **options,
    )
    assert result["ok"] and result["response"] == "Executed by " + profile
    assert len(worker_api.received) == 1
    received_profile, task, context_id = worker_api.received[0]
    assert received_profile == profile and context_id == result["context_id"]
    original = (
        message.removeprefix("@developer\n") if message.startswith("@") else message
    )
    assert task.startswith(original + "\n\nWorkspace: ")
    assert "\n\nWorkspace: " + str(worker_api.root / relative) in task
    if "app.py" in message:
        assert (
            "\nWorkspace files:\n" + str(worker_api.root / "nodepad/src/app.py") in task
        )
    assert any(event["state"] == "submitted" for event in result["events"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,options",
    [
        ("https://example.org/@reviewer", {}),
        ("```\n@reviewer example\n```", {}),
        ("@reviewer @developer inspect", {}),
        ("/unregistered-sdk inspect", {}),
        ("Have reviewer inspect file nodepad/missing.py", {}),
        ("Have reviewer inspect ../escape", {}),
        ("Repair the parser", {"profile": "invented-agent"}),
        ("Repair the parser", {"sdk": "invented-sdk"}),
        ("Repair the parser", {"profile": "developer", "workspace": "missing"}),
    ],
)
async def test_rejected_routes_never_create_or_run_a_worker(
    worker_api, message, options
):
    from agent import AgentContext

    before = {context.id for context in AgentContext.all()}
    result = await dispatch.dispatch(
        message,
        timeout=2,
        poll_interval=0.25,
        workspace_root=worker_api.root,
        **options,
    )
    assert not result.get("ok") or result["mode"] == "local"
    assert not worker_api.received
    assert {context.id for context in AgentContext.all()} == before
    if message.startswith("/unregistered"):
        assert result["state"] == "failed" and "Unknown SDK" in result["error"]


@pytest.mark.asyncio
async def test_actual_api_rejects_wrong_key_without_creating_context(worker_api):
    from agent import AgentContext

    before = {context.id for context in AgentContext.all()}
    code, _, _ = await dispatch._curl_json(
        worker_api.base + "/api/api_message",
        {"agent_profile": "reviewer", "message": "Test", "async": True},
        3,
        https_only=False,
        api_key="wrong-integration-token",
    )
    assert code == 401 and not worker_api.received
    assert {context.id for context in AgentContext.all()} == before
