"""Stable material projections: stdout/cursors/metrics never become messages."""

import hashlib
import json

from .security import clean

PUBLIC = {
    "ATTEMPT_COMPLETED": "ATTEMPT_COMPLETED",
    "BLOCKED": "NEEDS_YOU",
    "CONTROL_CHANGED": "CRITICAL_CONTROL_FAILURE",
    "MISSION_COMPLETED": "MISSION_COMPLETE",
    "REMOTE_UNAVAILABLE": "CRITICAL_INFRASTRUCTURE_FAILURE",
}
TERMINAL = {"completed", "failed", "canceled", "cancelled", "rejected"}


def event(campaign, kind, data, revision=None):
    payload = clean(data)
    identity = [
        campaign.campaign_id,
        campaign.remote_task_id,
        revision,
        kind,
        payload if revision is None else None,
    ]
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {
        "id": key,
        "type": kind,
        "revision": revision,
        "data": payload,
        "public": PUBLIC.get(kind),
    }


def reduce(campaign, remote):
    if type(remote.get("heartbeat_seq")) is int:
        campaign.heartbeat_seq = remote["heartbeat_seq"]
    if (
        remote.get("revision") is not None
        and remote.get("revision") == campaign.remote_revision
    ):
        return []
    old = campaign.material
    # Revision/heartbeat/log cursor alone is never material. A terminal state
    # cannot be turned into a mission completion without Argus Reviewer approval.
    material = {
        key: remote.get(key)
        for key in (
            "state",
            "stage",
            "run_id",
            "attempt_id",
            "source_sha",
            "evidence_revision",
            "blocked",
        )
    }
    events = []
    revision = remote.get("revision")
    if old and old == material:
        campaign.remote_revision = revision
        return []
    state = material["state"]
    if (
        state != old.get("state") or material["attempt_id"] != old.get("attempt_id")
    ) and state in TERMINAL:
        events.append(event(campaign, "ATTEMPT_COMPLETED", material, revision))
    elif state in {"input-required", "auth-required", "blocked"} or material["blocked"]:
        if state != old.get("state") or material["blocked"] != old.get("blocked"):
            events.append(event(campaign, "BLOCKED", material, revision))
    elif state != old.get("state") or material["stage"] != old.get("stage"):
        item = event(campaign, "STATE_CHANGED", material, revision)
        if material["stage"] != old.get("stage") and material["stage"]:
            item["public"] = "STAGE_TRANSITION"
        events.append(item)
    if material["evidence_revision"] and material["evidence_revision"] != old.get(
        "evidence_revision"
    ):
        events.append(
            event(
                campaign,
                "EVIDENCE_READY",
                {"evidence_revision": material["evidence_revision"]},
                revision,
            )
        )
    campaign.material = material
    campaign.remote_state = state
    campaign.remote_stage = material["stage"]
    campaign.remote_revision = revision
    for key in ("run_id", "attempt_id", "source_sha"):
        setattr(campaign, key, material[key])
    campaign.latest_evidence_ref = remote.get("evidence_ref")
    return [item for item in events if item["id"] not in campaign.events]
