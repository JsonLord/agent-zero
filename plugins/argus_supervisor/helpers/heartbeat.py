"""Deterministic campaign state machine; no model calls on unchanged ticks."""

import time
import uuid

from . import lease
from .event_reducer import event, reduce
from .models import AmbiguousMutation, SupervisorError, Unsupported
from .security import clean


class Supervisor:
    def __init__(
        self,
        store,
        client,
        argus,
        foreman=None,
        *,
        controller_id="argus-openoperator",
        ttl=600,
    ):
        self.store, self.client, self.argus, self.foreman = (
            store,
            client,
            argus,
            foreman,
        )
        self.controller_id, self.ttl = controller_id, ttl
        self.capabilities = {}
        self.last_tick = None
        self.last_error = None

    async def discover(self):
        self.capabilities = await self.client.discover()
        return self.capabilities

    def record(self, campaign, kind, data):
        item = event(campaign, kind, data, campaign.remote_revision)
        self.store.append_event(campaign, item)

    def control_lost(self, campaign):
        if lease.lose(campaign):
            self.record(
                campaign,
                "CONTROL_CHANGED",
                {"state": "CONTROL_LOST", "epoch": campaign.controller_epoch},
            )
        self.store.save(campaign)

    async def authority(self, campaign, epoch):
        if (
            campaign.mode != "controller"
            or type(epoch) is not int
            or epoch != campaign.controller_epoch
        ):
            raise SupervisorError("stale_controller_epoch")
        try:
            remote = await self.client.read_control(campaign.campaign_id)
            lease.verify(lease.snapshot(campaign), remote)
            if remote["controller_id"] != self.controller_id:
                raise SupervisorError("remote_control_not_owned")
        except SupervisorError:
            self.control_lost(campaign)
            raise
        return remote

    async def mutation(self, campaign, operation, params, epoch, *, approved=False):
        if campaign.intent:
            raise SupervisorError("unresolved_mutation_intent")
        if operation != "claim_control":
            await self.authority(campaign, epoch)
        if not self.client.capabilities.get(operation):
            raise Unsupported("unsupported_" + operation)
        if operation == "submit":
            if campaign.submitted_attempts >= campaign.max_attempts:
                raise SupervisorError("attempt_limit_reached")
            if campaign.remote_task_id and campaign.remote_state not in {
                "completed",
                "failed",
                "canceled",
                "cancelled",
                "rejected",
            }:
                raise SupervisorError("remote_attempt_already_active")
        request_id = uuid.uuid4().hex
        campaign.intent = {
            "request_id": request_id,
            "operation": operation,
            "state": "in_flight",
            "epoch": epoch,
            "argus_approved": approved,
        }
        if operation == "submit":
            campaign.submitted_attempts += 1
        self.store.save(campaign)
        try:
            if operation == "claim_control":
                result = await self.client.claim_control(
                    campaign.campaign_id, self.controller_id, self.ttl, request_id
                )
                readback = await self.client.read_control(campaign.campaign_id)
                lease.verify(result, readback)
                lease.accept(campaign, readback, self.controller_id)
            else:
                result = await self.client.mutate(
                    operation,
                    campaign.campaign_id,
                    lease.snapshot(campaign),
                    request_id,
                    **params,
                )
                if operation == "submit":
                    if not isinstance(result.get("id"), str) or not result["id"]:
                        raise AmbiguousMutation("mutation_outcome_unknown")
                    campaign.remote_task_id = result["id"]
                    campaign.material = {}
                    campaign.remote_revision = None
                    campaign.remote_state = "submitted"
                elif operation == "release_control":
                    remote = await self.client.read_control(campaign.campaign_id)
                    if (
                        lease.valid(remote)
                        and remote.get("controller_id") == self.controller_id
                    ):
                        raise AmbiguousMutation("release_not_confirmed")
                    lease.lose(campaign)
                elif operation == "renew_control":
                    readback = await self.client.read_control(campaign.campaign_id)
                    lease.verify(result, readback)
                    lease.accept(campaign, readback, self.controller_id)
            campaign.intent = None
            self.store.save(campaign)
            return clean(result)
        except BaseException:
            # Cancellation/process loss may happen after the remote commit.
            # Intent stays unresolved even when the local caller disappears.
            campaign.intent["state"] = "unknown"
            self.control_lost(campaign)
            campaign.pending_question = {
                "code": "mutation_outcome_unknown",
                "request_id": request_id,
            }
            self.store.save(campaign)
            raise

    async def recover_intent(self, campaign):
        if not campaign.intent:
            return
        result = await self.client.rpc(
            "request_status",
            {
                "campaign_id": campaign.campaign_id,
                "request_id": campaign.intent["request_id"],
            },
        )
        if result.get("request_id") != campaign.intent["request_id"] or result.get(
            "state"
        ) not in {"applied", "not_applied"}:
            raise SupervisorError("mutation_readback_inconclusive")
        if result["state"] == "applied" and campaign.intent["operation"] == "submit":
            if not isinstance(result.get("task_id"), str) or not result["task_id"]:
                raise SupervisorError("mutation_readback_missing_task")
            campaign.remote_task_id = result["task_id"]
        # Readback resolves the journal, never silently reclaims authority or resends.
        campaign.intent = None
        campaign.pending_question = None
        lease.lose(campaign)
        self.store.save(campaign)

    async def tick(self):
        self.last_tick = time.time()
        if not self.capabilities:
            try:
                await self.discover()
            except SupervisorError:
                self.last_error = "discovery_unavailable"
                return
        for campaign_id in self.store.ids():
            try:
                with self.store.lock(campaign_id):
                    campaign = self.store.load(campaign_id)
                    if campaign.paused or campaign.next_poll_at > time.time():
                        continue
                    await self.poll(campaign)
            except SupervisorError as error:
                # Stable codes only; continue other campaigns including corrupt ones.
                self.last_error = str(error)

    async def poll(self, campaign):
        if campaign.intent:
            self.control_lost(campaign)
        elif campaign.mode == "controller":
            try:
                remote = await self.authority(campaign, campaign.controller_epoch)
                if remote["expires_at"] - time.time() < self.ttl / 2:
                    await self.mutation(
                        campaign,
                        "renew_control",
                        {"ttl_seconds": self.ttl},
                        campaign.controller_epoch,
                    )
            except SupervisorError:
                self.control_lost(campaign)
        if not campaign.remote_task_id:
            self.store.save(campaign)
            await self.deliver(campaign)
            return
        try:
            remote = await self.client.status(campaign.remote_task_id)
        except SupervisorError:
            campaign.failures += 1
            campaign.next_poll_at = time.time() + min(
                1800, 30 * 2 ** min(campaign.failures, 5)
            )
            if campaign.failures == 3:
                self.record(
                    campaign, "REMOTE_UNAVAILABLE", {"reason": "status_unavailable"}
                )
            self.store.save(campaign)
            if campaign.failures == 3:
                await self.deliver(campaign)
            return
        campaign.failures, campaign.next_poll_at = 0, 0
        campaign.last_seen = time.time()
        events = reduce(campaign, remote)
        for item in events:
            self.store.append_event(campaign, item)
        self.store.save(campaign)
        await self.deliver(campaign)

    async def deliver(self, campaign):
        pending = [
            item for item in campaign.events.values() if item["delivery"] == "pending"
        ][:8]
        if not pending or not campaign.argus_project_id:
            return
        # Foreman only sees significant evidence, never routine status/log ticks.
        evidence = {}
        if campaign.remote_task_id and any(
            item["type"] in {"ATTEMPT_COMPLETED", "BLOCKED", "EVIDENCE_READY"}
            for item in pending
        ):
            try:
                evidence = await self.client.evidence(campaign.remote_task_id)
            except SupervisorError:
                evidence = {"unavailable": True}
        hint = {"directive": None, "hint": "none"}
        if self.foreman and evidence and not evidence.get("unavailable"):
            try:
                hint = await self.foreman.assess(campaign, evidence)
            except SupervisorError:
                hint = {"unavailable": True}  # advisory outage never blocks Argus
        if hint.get("directive") == "CONTINUE" and all(
            item["type"] == "EVIDENCE_READY" for item in pending
        ):
            for item in pending:
                item["delivery"] = "no_wake"
            self.store.save(campaign)
            return
        # Mark before invoking a model: restart must not duplicate a decision turn.
        for item in pending:
            item["delivery"] = "in_flight"
        self.store.save(campaign)
        try:
            result = await self.argus.notify(campaign, clean(pending), evidence, hint)
            campaign.argus_status = result.get("status", "observing")
            campaign.pending_question = result.get("pending_question")
            review = result.get("review") or {}
            campaign.reviewer_verdict = review.get("status")
            for item in pending:
                item["delivery"] = "delivered"
            self.store.save(campaign)
            await self.approved_action(campaign, result, pending)
        except SupervisorError as error:
            if str(error) == "argus_backend_not_configured":
                for item in pending:
                    item["delivery"] = "pending"
            campaign.argus_status = "unavailable"
            campaign.pending_question = {"code": "argus_turn_requires_review"}
            self.store.save(campaign)

    async def approved_action(self, campaign, result, delivered):
        # Never execute a prose directive or Foreman output. The pinned runtime's
        # independent Reviewer and this exact event must match the proposal.
        proposal = result.get("proposal")
        review = result.get("review") or {}
        if not proposal:
            return
        if (
            review.get("status") != "done"
            or review.get("source") != "reviewer"
            or result.get("review_bound_to_events")
            != [item["id"] for item in delivered]
            or campaign.mode != "controller"
            or not isinstance(proposal, dict)
            or proposal.get("event_id") not in {item["id"] for item in delivered}
        ):
            campaign.pending_question = {"code": "proposal_not_authorized"}
            self.store.save(campaign)
            return
        decision_id = proposal["event_id"]
        if decision_id in campaign.decision_receipts:
            return
        await self.authority(campaign, campaign.controller_epoch)
        # An interrupted relay must be inspected, never automatically repeated.
        campaign.decision_receipts.append(decision_id)
        self.store.save(campaign)
        operation = proposal.get("operation")
        if operation == "complete":
            if campaign.remote_state != "completed":
                raise SupervisorError("remote_attempt_not_completed")
            self.record(
                campaign,
                "MISSION_COMPLETED",
                {"reviewer_verdict": "done", "event_id": proposal["event_id"]},
            )
            campaign.events[campaign.latest_significant_event["id"]]["delivery"] = (
                "no_wake"
            )
            campaign.paused = True
            campaign.argus_status = "complete"
            self.store.save(campaign)
            return
        if operation not in {"submit", "intervene", "cancel"}:
            raise SupervisorError("proposal_operation_not_allowed")
        # No free-form shell, URLs, epoch, campaign ID or task switch in proposals.
        params = proposal.get("params", {})
        allowed = {
            "submit": {"text"},
            "intervene": {"instruction"},
            "cancel": {"reason"},
        }[operation]
        if (
            not isinstance(params, dict)
            or set(params) != allowed
            or any(not isinstance(v, str) or len(v) > 8000 for v in params.values())
        ):
            raise SupervisorError("proposal_parameters_invalid")
        if operation != "submit":
            params = {**params, "id": campaign.remote_task_id}
        await self.mutation(
            campaign, operation, params, campaign.controller_epoch, approved=True
        )
