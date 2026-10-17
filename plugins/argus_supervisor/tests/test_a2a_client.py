import pytest

from plugins.argus_supervisor.helpers.models import (
    AmbiguousMutation,
    SupervisorError,
    Unsupported,
)


@pytest.mark.asyncio
async def test_feature_detection_generic_a2a_is_read_only_without_leases(setup):
    s, remote, _ = setup
    remote.extension = False
    capabilities = await s.discover()
    assert capabilities["status"] and not capabilities["claim_control"]
    assert (await s.client.status("task-1"))["state"] == "working"
    with pytest.raises(Unsupported):
        await s.client.claim_control("campaign-1", "argus-openoperator", 600, "request")


@pytest.mark.asyncio
async def test_mutation_refused_without_valid_lease_even_when_client_called_directly(
    setup,
):
    s, remote, _ = setup
    with pytest.raises(SupervisorError):
        await s.client.mutate("cancel", "campaign-1", {}, "request", id="task-1")
    assert not any(method == "tasks/cancel" for method, _ in remote.calls)


@pytest.mark.asyncio
async def test_submit_is_nonblocking_and_timeout_is_never_replayed_after_restart(setup):
    from plugins.argus_supervisor.helpers.heartbeat import Supervisor

    s, remote, argus = setup
    c = s.store.load("campaign-1")
    c.remote_task_id = None
    s.store.save(c)
    await s.mutation(c, "claim_control", {}, None)
    remote.timeout = "message/send"
    with pytest.raises(AmbiguousMutation):
        await s.mutation(
            c, "submit", {"text": "Return a harmless status only"}, c.controller_epoch
        )
    restarted = Supervisor(s.store, s.client, argus)
    await restarted.tick()
    assert s.store.load(c.campaign_id).mode == "observer"
    assert s.store.load(c.campaign_id).intent["state"] == "unknown"
    sent = [params for method, params in remote.calls if method == "message/send"]
    assert len(sent) == 1 and sent[0]["configuration"]["blocking"] is False
    assert sent[0]["metadata"]["argus_supervisor"]["controller_epoch"] == 5
    await restarted.recover_intent(s.store.load(c.campaign_id))
    assert s.store.load(c.campaign_id).remote_task_id == "task-1"
    assert len([x for x in remote.calls if x[0] == "message/send"]) == 1


@pytest.mark.asyncio
async def test_task_identity_mismatch_is_rejected(setup):
    s, remote, _ = setup
    remote.task["id"] = "different"
    with pytest.raises(SupervisorError, match="identity"):
        await s.client.status("task-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", [[], {"jsonrpc": "2.0", "id": "wrong", "result": {}}, {"result": "bad"}]
)
async def test_malformed_remote_rpc_never_looks_successful(setup, payload):
    s, _, _ = setup

    async def transport(*args):
        return payload

    s.client.transport = transport
    with pytest.raises(SupervisorError, match="invalid_remote_result"):
        await s.client.status("task-1")


@pytest.mark.asyncio
async def test_rpc_timeout_and_cancellation_have_safe_mutation_semantics(setup):
    import asyncio

    s, _, _ = setup

    async def transport(*args):
        raise TimeoutError("Bearer sensitive-not-a-log-message")

    s.client.transport = transport
    with pytest.raises(AmbiguousMutation) as caught:
        await s.client.rpc("submit", {}, mutation=True)
    assert "sensitive" not in str(caught.value)

    async def cancel(*args):
        raise asyncio.CancelledError()

    s.client.transport = cancel
    with pytest.raises(asyncio.CancelledError):
        await s.client.rpc("submit", {}, mutation=True)
