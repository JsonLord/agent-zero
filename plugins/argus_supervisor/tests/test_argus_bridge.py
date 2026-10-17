import pytest

from plugins.argus_supervisor.helpers.argus_bridge import ArgusBridge
from plugins.argus_supervisor.helpers.models import SupervisorError


@pytest.mark.asyncio
async def test_unconfigured_runtime_does_not_fake_model_turn(setup):
    s, _, _ = setup
    bridge = ArgusBridge(s.store.root / "argus", backend="")
    with pytest.raises(SupervisorError, match="backend_not_configured"):
        await bridge.notify(s.store.load("campaign-1"), [], {}, {})


@pytest.mark.asyncio
async def test_unreviewed_or_old_review_cannot_authorize_a_proposal(setup):
    s, remote, _argus = setup
    c = s.store.load("campaign-1")
    await s.mutation(c, "claim_control", {}, None)
    result = {
        "review": {"status": "done", "source": "reviewer"},
        "proposal": {
            "operation": "cancel",
            "params": {"reason": "stop"},
            "event_id": "e1",
        },
    }
    await s.approved_action(c, result, [{"id": "e1"}])
    assert c.pending_question["code"] == "proposal_not_authorized"
    assert not any(method == "tasks/cancel" for method, _ in remote.calls)


@pytest.mark.asyncio
async def test_fresh_reviewer_decision_relays_through_lease_gate(setup):
    s, remote, _ = setup
    c = s.store.load("campaign-1")
    await s.mutation(c, "claim_control", {}, None)
    result = {
        "review": {"status": "done", "source": "reviewer"},
        "review_bound_to_events": ["e1"],
        "proposal": {
            "operation": "cancel",
            "params": {"reason": "bounded test"},
            "event_id": "e1",
        },
    }
    await s.approved_action(c, result, [{"id": "e1"}])
    assert len([x for x in remote.calls if x[0] == "tasks/cancel"]) == 1
    await s.approved_action(c, result, [{"id": "e1"}])
    result["proposal"]["event_id"] = "e2"
    result["review_bound_to_events"] = ["e2"]
    remote.lease["epoch"] += 1
    with pytest.raises(SupervisorError):
        await s.approved_action(c, result, [{"id": "e2"}])
    assert len([x for x in remote.calls if x[0] == "tasks/cancel"]) == 1


@pytest.mark.asyncio
async def test_attempt_is_not_mission_completion_without_fresh_reviewer(setup):
    s, _, _ = setup
    c = s.store.load("campaign-1")
    c.remote_state = "completed"
    await s.mutation(c, "claim_control", {}, None)
    proposal = {"operation": "complete", "params": {}, "event_id": "e1"}
    await s.approved_action(c, {"proposal": proposal}, [{"id": "e1"}])
    assert c.argus_status != "complete"
    await s.approved_action(
        c,
        {
            "proposal": proposal,
            "review": {"status": "done", "source": "reviewer"},
            "review_bound_to_events": ["e1"],
        },
        [{"id": "e1"}],
    )
    assert c.argus_status == "complete" and c.paused
    assert len([e for e in c.events.values() if e["type"] == "MISSION_COMPLETED"]) == 1
