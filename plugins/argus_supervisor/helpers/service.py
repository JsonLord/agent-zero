"""Normal plugin lifecycle/config/API owner; no auxiliary listener or scheduler."""

import os
import threading
import time
import uuid
from pathlib import Path

from .a2a_client import OpenTrainingA2AClient
from .argus_bridge import ArgusBridge
from .campaign_store import CampaignStore
from .foreman_bridge import ForemanBridge
from .heartbeat import Supervisor
from .models import CampaignState, SupervisorError
from .security import clean, identifier

_instance = None
_last_run = 0
_task = None
_kick_lock = threading.Lock()


def enabled():
    return os.getenv("ARGUS_SUPERVISOR_ENABLED", "0").lower() in {"1", "true"}


def get():
    global _instance
    if not enabled():
        raise SupervisorError("supervisor_disabled")
    if _instance is None:
        root = os.getenv("ARGUS_SUPERVISOR_STATE_ROOT", "/a0/usr/argus-supervisor")
        store = CampaignStore(root)
        client = OpenTrainingA2AClient(
            os.getenv("OPENTRAINING_A2A_URL", ""),
            os.getenv("OPENTRAINING_A2A_TOKEN", ""),
            os.getenv("OPENTRAINING_A2A_PROJECT"),
        )
        home = os.getenv("ARGUS_SUPERVISOR_ARGUS_HOME", str(store.root / "argus-home"))
        if not Path(home).resolve().is_relative_to(store.root.resolve()):
            raise SupervisorError("argus_home_must_be_under_state_root")
        argus = ArgusBridge(home)
        foreman = (
            ForemanBridge(str(store.root / "foreman-home"))
            if os.getenv("ARGUS_SUPERVISOR_FOREMAN_ENABLED", "0") == "1"
            else None
        )
        _instance = Supervisor(
            store,
            client,
            argus,
            foreman,
            controller_id=os.getenv(
                "ARGUS_SUPERVISOR_CONTROLLER_ID", "argus-openoperator"
            ),
            ttl=max(
                60,
                min(3600, int(os.getenv("ARGUS_SUPERVISOR_LEASE_TTL_SECONDS", "600"))),
            ),
        )
    return _instance


async def heartbeat(force=False):
    global _last_run
    if not enabled():
        return
    service = get()
    cadence = max(60, int(os.getenv("ARGUS_SUPERVISOR_HEARTBEAT_SECONDS", "120")))
    if not force and time.monotonic() - _last_run < cadence:
        return
    try:
        with service.store.lock():
            _last_run = time.monotonic()
            if force:
                try:
                    try:
                        await service.argus.verify()
                    except SupervisorError:
                        service.last_error = "argus_runtime_unavailable"
                    if service.foreman:
                        try:
                            await service.foreman.verify()
                        except SupervisorError:
                            service.last_error = "foreman_runtime_unavailable"
                    await service.discover()
                    for campaign_id in service.store.ids():
                        with service.store.lock(campaign_id):
                            campaign = service.store.load(campaign_id)
                            if campaign.argus_project_id:
                                try:
                                    result = await service.argus.status(campaign)
                                    campaign.argus_status = result.get(
                                        "status", "observing"
                                    )
                                    campaign.pending_question = result.get(
                                        "pending_question"
                                    )
                                    if any(
                                        e["delivery"] == "in_flight"
                                        for e in campaign.events.values()
                                    ):
                                        campaign.pending_question = {
                                            "code": "argus_turn_requires_review"
                                        }
                                    service.store.save(campaign)
                                except SupervisorError:
                                    campaign.argus_status = "unavailable"
                                    service.store.save(campaign)
                except SupervisorError:
                    service.last_error = "recovery_unavailable"
            await service.tick()
            service.store.atomic(
                service.store.root / "state/supervisor.json",
                {
                    "last_tick": service.last_tick,
                    "last_error": service.last_error,
                    "capabilities": service.capabilities,
                },
            )
    except SupervisorError:
        service.last_error = "supervisor_tick_unavailable"


def public(campaign):
    return clean(
        {
            key: getattr(campaign, key)
            for key in (
                "campaign_id",
                "objective",
                "remote_task_id",
                "run_id",
                "attempt_id",
                "source_sha",
                "remote_state",
                "remote_stage",
                "remote_revision",
                "mode",
                "controller_id",
                "controller_epoch",
                "lease_expires_at",
                "argus_project_id",
                "argus_status",
                "pending_question",
                "reviewer_verdict",
                "paused",
                "last_seen",
                "latest_evidence_ref",
            )
        }
    ) | {
        "events": [
            clean(item) for item in campaign.events.values() if item.get("public")
        ][-30:],
        "unresolved_intent": bool(campaign.intent),
    }


async def action(campaign_id, operation, params):
    service = get()
    with service.store.lock(identifier(campaign_id)):
        campaign = service.store.load(campaign_id)
        if not service.capabilities:
            await service.discover()
        if operation == "observe":
            await service.poll(campaign)
        elif operation == "mission":
            await service.argus.bind(campaign)
            service.record(campaign, "STATE_CHANGED", {"reason": "mission_bound"})
        elif operation in {"pause", "resume"}:
            campaign.paused = operation == "pause"
        elif operation == "claim":
            if not service.client.capabilities.get("read_control"):
                raise SupervisorError("remote_lease_readback_unsupported")
            await service.mutation(campaign, "claim_control", {}, None)
        elif operation == "release":
            await service.mutation(campaign, "release_control", {}, params.get("epoch"))
        elif operation in {"submit", "intervene", "cancel"}:
            fields = {
                "submit": {"text"},
                "intervene": {"instruction"},
                "cancel": {"reason"},
            }[operation]
            values = {key: params.get(key) for key in fields}
            if any(
                not isinstance(v, str) or not v.strip() or len(v) > 8000
                for v in values.values()
            ):
                raise SupervisorError("invalid_action_parameters")
            values = {key: clean(value) for key, value in values.items()}
            if operation != "submit":
                if not campaign.remote_task_id:
                    raise SupervisorError("no_remote_task")
                values["id"] = campaign.remote_task_id
            await service.mutation(campaign, operation, values, params.get("epoch"))
        elif operation == "resolve_intent":
            await service.recover_intent(campaign)
        elif operation == "answer":
            answer = params.get("answer")
            if not isinstance(answer, str) or not answer.strip() or len(answer) > 8000:
                raise SupervisorError("invalid_answer")
            result = await service.argus.answer(campaign, clean(answer))
            campaign.pending_question = result.get("pending_question")
            from .event_reducer import event

            service.store.append_event(
                campaign,
                event(
                    campaign,
                    "STATE_CHANGED",
                    {"reason": "operator_answered"},
                    uuid.uuid4().hex,
                ),
            )
        else:
            raise SupervisorError("unsupported_action")
        service.store.save(campaign)
        return public(campaign)


def create(input):
    objective = input.get("objective")
    if not isinstance(objective, str) or not objective.strip() or len(objective) > 8000:
        raise SupervisorError("invalid_objective")
    task_id = input.get("remote_task_id")
    if task_id is not None and (
        not isinstance(task_id, str) or not task_id or len(task_id) > 256
    ):
        raise SupervisorError("invalid_remote_task_id")
    attempts = input.get("max_attempts", 3)
    if type(attempts) is not int or not 1 <= attempts <= 20:
        raise SupervisorError("invalid_attempt_limit")
    campaign = CampaignState(
        identifier(input.get("campaign_id")),
        clean(objective),
        remote_task_id=task_id,
        max_attempts=attempts,
    )
    get().store.create(campaign)
    return public(campaign)


def kick(force=False):
    """Schedule one bounded tick using the framework's retained task owner."""
    global _task
    from helpers.defer import DeferredTask

    with _kick_lock:
        if not enabled():
            if _task and not _task.is_ready():
                _task.kill()
            return
        if _task and not _task.is_ready():
            return
        _task = DeferredTask("ArgusSupervisor").start_task(heartbeat, force=force)
