import time

import pytest

from plugins.argus_supervisor.helpers import lease
from plugins.argus_supervisor.helpers.models import SupervisorError


@pytest.mark.asyncio
async def test_claim_renew_release_and_stale_epoch(setup):
    s, remote, _ = setup
    c = s.store.load("campaign-1")
    await s.mutation(c, "claim_control", {}, None)
    assert c.mode == "controller" and c.controller_epoch == 5
    with pytest.raises(SupervisorError, match="stale"):
        await s.mutation(c, "cancel", {"id": "task-1"}, 4)
    await s.mutation(c, "renew_control", {"ttl_seconds": 600}, 5)
    await s.mutation(c, "release_control", {}, 5)
    assert c.mode == "observer" and not remote.lease


@pytest.mark.asyncio
async def test_lost_remote_lease_moves_observer_once(setup):
    s, remote, _ = setup
    c = s.store.load("campaign-1")
    lease.accept(c, remote.lease, s.controller_id)
    s.store.save(c)
    remote.lease["epoch"] += 1
    await s.tick()
    first = s.store.load(c.campaign_id)
    assert first.mode == "observer"
    losses = [e for e in first.events.values() if e["type"] == "CONTROL_CHANGED"]
    assert len(losses) == 1
    await s.tick()
    assert (
        len(
            [
                e
                for e in s.store.load(c.campaign_id).events.values()
                if e["type"] == "CONTROL_CHANGED"
            ]
        )
        == 1
    )
    assert not any(method == "campaign/claim_control" for method, _ in remote.calls)


@pytest.mark.parametrize(
    "change", [{"epoch": 9}, {"expires_at": 0}, {"controller_id": "other"}]
)
def test_remote_identity_epoch_and_expiry_gate(change):
    local = {
        "controller_id": "argus-openoperator",
        "epoch": 1,
        "expires_at": time.time() + 600,
    }
    with pytest.raises(SupervisorError):
        lease.verify(local, {**local, **change})


@pytest.mark.asyncio
async def test_renewal_timeout_immediately_loses_control_but_keeps_observing(setup):
    s, remote, _ = setup
    c = s.store.load("campaign-1")
    remote.lease["expires_at"] = time.time() + 30
    lease.accept(c, remote.lease, s.controller_id)
    s.store.save(c)
    remote.timeout = "campaign/renew_control"
    await s.tick()
    saved = s.store.load(c.campaign_id)
    assert saved.mode == "observer" and saved.remote_state == "working"
    assert saved.intent["operation"] == "renew_control"
    assert (
        len([e for e in saved.events.values() if e["type"] == "CONTROL_CHANGED"]) == 1
    )


@pytest.mark.asyncio
async def test_takeover_between_readback_and_write_is_rejected_remotely(setup):
    from plugins.argus_supervisor.helpers.models import AmbiguousMutation

    s, remote, _ = setup
    c = s.store.load("campaign-1")
    await s.mutation(c, "claim_control", {}, None)
    original = remote.transport

    async def race(method, suffix, payload):
        if payload and payload["method"] == "tasks/cancel":
            remote.lease["epoch"] += 1
        return await original(method, suffix, payload)

    s.client.transport = race
    with pytest.raises(AmbiguousMutation):
        await s.mutation(c, "cancel", {"id": "task-1"}, c.controller_epoch)
    assert "tasks/cancel" not in remote.applied_mutations
    assert c.mode == "observer" and c.intent["state"] == "unknown"
