import pytest

from plugins.argus_supervisor.helpers.heartbeat import Supervisor
from plugins.argus_supervisor.helpers.models import SupervisorError


@pytest.mark.asyncio
async def test_unchanged_tick_and_routine_stdout_do_not_call_models_or_message_chat(
    setup,
):
    s, remote, argus = setup
    await s.tick()
    argus.calls.clear()
    remote.task["history"] = [{"text": "checked git; still running; step 300"}]
    remote.task["metadata"]["argus_supervisor"]["revision"] = "2"
    await s.tick()
    assert not argus.calls
    public = [e for e in s.store.load("campaign-1").events.values() if e.get("public")]
    assert len(public) == 1 and public[0]["public"] == "STAGE_TRANSITION"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["completed", "failed", "input-required"])
async def test_terminal_and_blocker_wake_once_across_restart(setup, state):
    s, remote, argus = setup
    await s.tick()
    argus.calls.clear()
    remote.task["status"]["state"] = state
    remote.task["metadata"]["argus_supervisor"]["revision"] = "2"
    await s.tick()
    assert len(argus.calls) == 1
    restarted = Supervisor(s.store, s.client, argus)
    await restarted.tick()
    assert len(argus.calls) == 1
    assert not any(method == "message/send" for method, _ in remote.calls)


@pytest.mark.asyncio
async def test_transient_read_backoff_and_threshold_do_not_invent_task_failure(
    setup, monkeypatch
):
    s, _remote, argus = setup

    async def unavailable(*args):
        raise SupervisorError("remote_transport_or_payload_error")

    monkeypatch.setattr(s.client, "status", unavailable)
    for _ in range(4):
        c = s.store.load("campaign-1")
        c.next_poll_at = 0
        s.store.save(c)
        await s.tick()
    c = s.store.load("campaign-1")
    assert c.remote_state == "unknown" and c.next_poll_at > c.updated_at
    assert len([e for e in c.events.values() if e["type"] == "REMOTE_UNAVAILABLE"]) == 1
    assert len(argus.calls) == 1


@pytest.mark.asyncio
async def test_inflight_model_turn_after_restart_is_not_repeated(setup):
    s, _, argus = setup
    c = s.store.load("campaign-1")
    c.events["interrupted"] = {
        "id": "interrupted",
        "type": "BLOCKED",
        "delivery": "in_flight",
    }
    s.store.save(c)
    await s.tick()
    assert all(e["id"] != "interrupted" for events, _, _ in argus.calls for e in events)
