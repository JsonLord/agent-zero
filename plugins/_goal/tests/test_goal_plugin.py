from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent import Agent, LoopData, AgentContext
from helpers import extension, files, mcp_handler
from helpers.llm_result import LLMResult
from helpers.log import Log
from plugins._goal.api.goal import Goal as GoalApi
from plugins._goal.commands import goal_command
from plugins._goal.tools import goal
from plugins._goal.tools.goal import GoalTool
from plugins._goal.tools.response import ResponseTool


@pytest.fixture(autouse=True)
def _isolate_goal_state(tmp_path, monkeypatch):
    """Ensure every goal test gets a clean isolated goal storage root and AgentContext state."""
    real_get_abs_path = files.get_abs_path
    def fake_get_abs_path(*parts):
        if parts and parts[0] == files.USER_DIR and len(parts) > 1 and parts[1] == files.PLUGINS_DIR:
            return str(tmp_path.joinpath(*parts))
        return real_get_abs_path(*parts)

    monkeypatch.setattr(files, "get_abs_path", fake_get_abs_path)
    monkeypatch.setattr(AgentContext, "get", lambda context_id: None)


@pytest.fixture()
def context_id():
    context_id = f"goal-test-{uuid.uuid4().hex}"
    yield context_id
    try:
        goal.delete_goal(context_id)
    except Exception:
        pass


def _payload(context_id: str, command_text: str) -> dict:
    from plugins._commands.helpers.commands import parse_slash_invocation

    return {
        "invocation": parse_slash_invocation(command_text),
        "context": {"context_id": context_id},
    }


def test_goal_storage_round_trip(context_id: str):
    current_goal = goal.create_goal(context_id, "Ship the goal plugin", token_budget=1200)

    loaded = goal.get_goal(context_id)
    assert loaded == current_goal
    assert loaded["status"] == "active"
    assert loaded["token_budget"] == 1200
    assert loaded["active_since"]
    assert loaded["elapsed_seconds"] == 0

    updated = goal.update_goal(context_id, status="paused", objective="Polish the goal strip")
    assert updated["status"] == "paused"
    assert updated["objective"] == "Polish the goal strip"
    assert updated["active_since"] == ""
    paused_seconds = updated["elapsed_seconds"]

    resumed = goal.resume_goal(context_id)
    assert resumed["status"] == "active"
    assert resumed["active_since"]
    assert resumed["elapsed_seconds"] == paused_seconds

    goal.delete_goal(context_id)
    assert goal.get_goal(context_id) is None


def test_goal_changes_publish_state_revision(context_id: str, monkeypatch):
    from agent import AgentContext
    from helpers import state_monitor_integration

    revisions = [1.0, 2.0, 3.0]
    rev_idx = [0]
    def get_next_time():
        val = revisions[min(rev_idx[0], len(revisions) - 1)]
        rev_idx[0] += 1
        return val

    output_data = {}
    dirty = []
    context = SimpleNamespace(
        set_output_data=lambda key, value: output_data.__setitem__(key, value)
    )
    monkeypatch.setattr(AgentContext, "get", lambda _context_id: context)
    monkeypatch.setattr(goal.time, "time", get_next_time)
    monkeypatch.setattr(
        state_monitor_integration,
        "mark_dirty_for_context",
        lambda context_id, *, reason: dirty.append((context_id, reason)),
    )

    goal.create_goal(context_id, "Publish changes")
    goal.update_goal(context_id, status="paused")
    goal.delete_goal(context_id)

    assert output_data["_goal_revision"] == 3.0
    assert dirty == [(context_id, "plugins._goal")] * 3


def test_goal_webui_uses_state_revisions_instead_of_polling():
    plugin_root = Path(__file__).resolve().parents[1]
    store = (plugin_root / "webui" / "goal-store.js").read_text()
    strip = (
        plugin_root
        / "extensions"
        / "webui"
        / "chat-input-progress-start"
        / "goal-strip.html"
    ).read_text()
    refresh = (
        plugin_root
        / "extensions"
        / "webui"
        / "apply_snapshot_before"
        / "refresh-goal.js"
    ).read_text()

    assert "setInterval(() => this.refresh" not in store
    assert "$watch('$store.chats.selected'" not in strip
    assert "_goal_revision" in refresh
    assert "goalStore.refresh(true)" in refresh


def test_goal_composer_menu_prefills_without_sending():
    plugin_root = Path(__file__).resolve().parents[1]
    injector = (
        plugin_root
        / "extensions"
        / "webui"
        / "initFw_end"
        / "goal-menu-injector.js"
    ).read_text()

    assert 'chatInputStore.message = "/goal ";' in injector
    assert "chatInputStore.focus();" in injector
    assert "sendMessage" not in injector


@pytest.mark.skipif(not shutil.which("node"), reason="node is required")
def test_goal_webui_uses_shared_hour_aware_duration_formatter():
    project_root = Path(__file__).resolve().parents[3]
    time_utils = (project_root / "webui" / "js" / "time-utils.js").read_bytes()
    module_url = "data:text/javascript;base64," + base64.b64encode(time_utils).decode("ascii")
    script = f"""
import {{ formatDuration }} from {module_url!r};
if (formatDuration(3_782_000) !== "1h3m2s") throw new Error("hours");
if (formatDuration(62_000) !== "1m2s") throw new Error("minutes");
"""
    subprocess.run(["node", "--input-type=module", "-e", script], check=True)

    store = (project_root / "plugins" / "_goal" / "webui" / "goal-store.js").read_text()
    assert 'import { formatDuration } from "/js/time-utils.js";' in store
    assert "return formatDuration(this.elapsedSeconds * 1000);" in store


def test_goal_command_sets_pauses_resumes_and_deletes(context_id: str, monkeypatch):
    class FakeContext:
        def __init__(self, context_id):
            self.id = context_id
            self.paused = True
            self.running = False

        def is_running(self):
            return self.running

        def communicate(self, message):
            self.running = True
            self.paused = False

        def set_output_data(self, key, value):
            pass

    context = FakeContext(context_id)
    monkeypatch.setattr(AgentContext, "get", lambda cid: context if cid == context_id else None)

    created = goal_command.run(_payload(context_id, "/goal Add current goal support"))
    assert created["effects"][0]["message"] == "Goal set."
    assert created["effects"][2] == {"type": "send_message", "text": "Add current goal support"}
    assert goal.get_goal(context_id)["objective"] == "Add current goal support"

    paused = goal_command.run(_payload(context_id, "/goal pause"))
    assert paused["effects"][0]["message"] == "Goal paused."
    assert goal.get_goal(context_id)["status"] == "paused"

    resumed = goal_command.run(_payload(context_id, "/goal resume"))
    assert resumed["effects"][0]["message"] == "Goal resumed."
    assert goal.get_goal(context_id)["status"] == "active"

    deleted = goal_command.run(_payload(context_id, "/goal delete"))
    assert deleted["effects"][0]["message"] == "Goal deleted."
    assert goal.get_goal(context_id) is None


def test_goal_auto_fills_prompt(context_id: str):
    result = goal_command.run(_payload(context_id, "/goal auto keep this tight"))

    assert "Create and own a durable goal" in result["text"]
    assert "User hint: keep this tight" in result["text"]
    assert result["effects"] == []


def test_goal_files_stay_under_user_plugin_state(context_id: str):
    goal.create_goal(context_id, "Keep state in usr")
    hashed_filename = f"{hashlib.sha256(context_id.encode()).hexdigest()}.json"
    goal_path = files.get_abs_path(
        files.USER_DIR,
        files.PLUGINS_DIR,
        goal.PLUGIN_NAME,
        goal.GOALS_DIR,
        hashed_filename,
    )

    assert files.exists(goal_path)


@pytest.mark.asyncio
async def test_goal_api_and_agent_tools(context_id: str):
    handler = object.__new__(GoalApi)
    created = await handler.process(
        {
            "action": "set",
            "context_id": context_id,
            "objective": "Exercise API path",
            "success_criteria": ["api criterion"],
        },
        None,
    )
    assert created["ok"] is True
    assert created["goal"]["objective"] == "Exercise API path"

    fake_agent = SimpleNamespace(context=SimpleNamespace(id=context_id))
    get_tool = GoalTool(fake_agent, "goal", None, {}, "", None)
    get_response = await get_tool.execute()
    assert "Exercise API path" in get_response.message

    checkpoint_tool = GoalTool(fake_agent, "goal", None, {}, "", None)
    await checkpoint_tool.execute(action="checkpoint", criterion_updates=[{"criterion": "api criterion", "state": "PASS"}])

    update_tool = GoalTool(fake_agent, "goal", None, {}, "", None)
    update_response = await update_tool.execute(action="update", status="completed")
    assert "Status: completed" in update_response.message

    create_tool = GoalTool(fake_agent, "goal", None, {}, "", None)
    create_response = await create_tool.execute(action="create", objective="Exercise tool path")
    assert "Goal created: Exercise tool path" == create_response.message
    assert goal.get_goal(context_id)["created_by"] == "model"


@pytest.mark.parametrize("terminal_status", ["blocked", "completed"])
@pytest.mark.asyncio
async def test_editing_terminal_goal_requests_agent_reactivation(
    context_id: str,
    terminal_status: str,
):
    goal.create_goal(context_id, "Initial goal")
    if terminal_status == "completed":
        goal.complete_goal(context_id)
    else:
        goal.update_goal(context_id, status=terminal_status)

    response = await object.__new__(GoalApi).process(
        {
            "action": "revise",
            "context_id": context_id,
            "objective": "Continue with the edited goal",
        },
        None,
    )

    assert response["ok"] is True
    assert response["goal"]["objective"] == "Continue with the edited goal"
    # Revise updates definition/history but does NOT silently reactivate or change terminal state
    assert response["goal"]["status"] == ("partially_verified" if terminal_status == "completed" else terminal_status)


@pytest.mark.asyncio
async def test_active_goal_keeps_response_tool_running(context_id: str):
    goal.create_goal(context_id, "Keep going")
    recorded = []
    fake_agent = SimpleNamespace(
        context=SimpleNamespace(id=context_id),
        hist_add_tool_result=lambda *args, **kwargs: recorded.append((args, kwargs)),
    )
    loop_data = SimpleNamespace(params_temporary={})
    tool = ResponseTool(
        fake_agent,
        "response",
        None,
        {"text": "Can you decide?"},
        "",
        loop_data,
    )

    response = await tool.execute()
    assert response.break_loop is False
    response.additional["_responses_output_item"] = {"type": "function_call_output"}
    await tool.after_execution(response)
    assert recorded == [
        (
            ("response", response.message),
            {"_responses_output_item": {"type": "function_call_output"}},
        )
    ]

    goal.update_goal(context_id, status="cancelled")
    response = await tool.execute()
    assert response.break_loop is True
    assert response.message == "Can you decide?"


@pytest.mark.asyncio
async def test_native_responses_text_uses_active_goal_response_override(
    context_id: str,
    monkeypatch,
):
    goal.create_goal(context_id, "Keep going")
    recorded = []

    async def no_op(*args, **kwargs):
        return None

    class NoMcpTools:
        def get_tool(self, agent, tool_name):
            return None

    agent = object.__new__(Agent)
    agent.context = SimpleNamespace(id=context_id, log=Log())
    agent.loop_data = LoopData()
    agent.data = {}
    agent.handle_intervention = no_op
    agent._log_response_builtin_items = no_op
    agent.hist_add_tool_result = lambda *args, **kwargs: recorded.append((args, kwargs))

    def get_tool(name, method, args, message, loop_data, **kwargs):
        return ResponseTool(agent, name, method, args, message, loop_data)

    agent.get_tool = get_tool
    monkeypatch.setattr(extension, "call_extensions_async", no_op)
    monkeypatch.setattr(mcp_handler.MCPConfig, "get_instance", lambda: NoMcpTools())

    result = await Agent.process_llm_result_tools(
        agent,
        LLMResult(response="Checkpoint for the user."),
    )

    assert result is None
    assert recorded[0][0][0] == "response"
    assert recorded[0][0][1].startswith("Goal still active.")
    assert recorded[0][1] == {}

    goal.update_goal(context_id, status="cancelled")
    result = await Agent.process_llm_result_tools(
        agent,
        LLMResult(response="Finished."),
    )

    assert result == "Finished."


def test_structured_goal_revision_checkpoint_and_evidence_completion(context_id: str):
    current=goal.create_goal(
        context_id,"Ship safely",owner_profile="developer",
        success_criteria=["tests pass","live verified"],constraints=["no secrets"],
        evidence_required=["test report"],autonomy={"level":"implementation"},
    )
    assert current["goal_id"].startswith("goal_")
    assert current["goal_revision"]==1 and current["progress_revision"]==1
    unchanged=goal.checkpoint_goal(context_id)
    assert unchanged["progress_revision"]==1
    checkpoint=goal.checkpoint_goal(context_id,milestone="testing",note="suite running",evidence=["pytest.xml"])
    assert checkpoint["progress_revision"]==2
    revised=goal.revise_goal(context_id,constraints=["no secrets","no PR"])
    assert revised["goal_revision"]==2 and revised["history"][0]["revision"]==1
    partial=goal.complete_goal(context_id)
    assert partial["status"]=="partially_verified" and partial["requires_attention"] is True
    goal.checkpoint_goal(context_id,criterion_updates=[
        {"criterion":"tests pass","state":"PASS","evidence":["38 passed"]},
        {"criterion":"live verified","state":"PASS","evidence":["smoke.json"]},
    ])
    completed=goal.complete_goal(context_id)
    assert completed["status"]=="completed" and completed["requires_attention"] is False


def test_attention_pause_resume_cancel_and_idempotency(context_id: str, monkeypatch):
    class FakeContext:
        def __init__(self, context_id):
            self.id = context_id
            self.paused = True
            self.running = False

        def is_running(self):
            return self.running

        def communicate(self, message):
            self.running = True
            self.paused = False

        def set_output_data(self, key, value):
            pass

    context = FakeContext(context_id)
    monkeypatch.setattr(AgentContext, "get", lambda cid: context if cid == context_id else None)

    first=goal.create_goal(context_id,"Need approval",idempotency_key="request-1",idempotency_scope="submission")
    replay=goal.create_goal("different-context","Duplicate",idempotency_key="request-1",idempotency_scope="submission")
    assert replay["goal_id"]==first["goal_id"] and replay["context_id"]==context_id
    attention=goal.checkpoint_goal(context_id,requires_attention=True,attention_reason="approval_required",attention_message="deploy ready")
    assert attention["requires_attention"] is True
    assert goal.update_goal(context_id,status="paused")["status"]=="paused"
    assert goal.resume_goal(context_id)["status"]=="active"
    assert goal.update_goal(context_id,status="cancelled")["status"]=="cancelled"


def test_subgoal_linkage_dependencies_and_resource_state(context_id: str):
    parent=goal.create_goal(context_id,"Parent")
    dependency=goal.create_goal(context_id+"-dependency","Diagnose",parent_goal_id=parent["goal_id"],success_criteria=["diagnosed"])
    child=goal.create_goal(context_id+"-child","Patch",parent_goal_id=parent["goal_id"],depends_on=[dependency["goal_id"]])
    assert child["parent_goal_id"]==parent["goal_id"] and goal.dependencies_ready(child) is False
    goal.checkpoint_goal(dependency["context_id"],criterion_updates=[{"criterion":"diagnosed","state":"PASS"}])
    goal.complete_goal(dependency["context_id"])
    assert goal.dependencies_ready(goal.get_goal(child["context_id"])) is True
    children={item["goal_id"] for item in goal.list_child_goals(parent["goal_id"])}
    assert children=={dependency["goal_id"],child["goal_id"]}
    goal.delete_goal(dependency["context_id"]); goal.delete_goal(child["context_id"])


def test_internal_delegate_endpoint_requires_api_key_not_browser_csrf():
    from plugins._goal.api.delegate import Delegate
    assert Delegate.requires_auth() is False
    assert Delegate.requires_csrf() is False
    assert Delegate.requires_api_key() is True


@pytest.mark.asyncio
async def test_internal_delegate_rejects_unknown_profile_before_context_creation(monkeypatch):
    from plugins._goal.api import delegate
    monkeypatch.setattr(delegate.subagents,"get_available_agents_dict",lambda project:{"reviewer":object()})
    initialize=MagicMock()
    monkeypatch.setattr(delegate,"initialize_agent",initialize)
    response=await object.__new__(delegate.Delegate).process({"agent_profile":"definitely-not-real","objective":"inspect"},None)
    assert response.status_code==404
    initialize.assert_not_called()


def test_dependency_aware_swarm_transitions_and_keeps_child_evidence(context_id: str):
    parent=goal.create_goal(context_id,"Fix feature",success_criteria=["tests pass","review passes"])
    debugger=goal.create_goal(context_id+"-debugger","Diagnose",owner_profile="debugger",parent_goal_id=parent["goal_id"],success_criteria=["diagnosed"])
    security=goal.create_goal(context_id+"-security","Review boundary",owner_profile="security",parent_goal_id=parent["goal_id"])
    patch=goal.create_goal(context_id+"-patch","Implement",owner_profile="tiny-coder",parent_goal_id=parent["goal_id"],depends_on=[debugger["goal_id"]],success_criteria=["implemented"])
    tester=goal.create_goal(context_id+"-tester","Test",owner_profile="tester",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    reviewer=goal.create_goal(context_id+"-reviewer","Review",owner_profile="reviewer",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    assert debugger["context_id"]!=security["context_id"]
    goal.checkpoint_goal(debugger["context_id"],criterion_updates=[{"criterion":"diagnosed","state":"PASS","evidence":["root cause"]}])
    goal.complete_goal(debugger["context_id"],result={"evidence":["root cause"]})
    assert goal.get_goal(patch["context_id"])["status"]=="interrupted"
    goal.checkpoint_goal(patch["context_id"],criterion_updates=[{"criterion":"implemented","state":"PASS","evidence":["feature.py"]}])
    goal.complete_goal(patch["context_id"],result={"changes":["feature.py"]})
    assert goal.get_goal(tester["context_id"])["status"]=="interrupted"
    assert goal.get_goal(reviewer["context_id"])["status"]=="interrupted"
    assert goal.get_goal(debugger["context_id"])["result"]["evidence"]==["root cause"]
    for child in (debugger,security,patch,tester,reviewer): goal.delete_goal(child["context_id"])
