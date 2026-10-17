"""Versioned durable state; no transport credentials belong in these records."""

import time
from dataclasses import asdict, dataclass, field


@dataclass
class CampaignState:
    campaign_id: str
    objective: str
    remote_task_id: str | None = None
    run_id: str | None = None
    attempt_id: str | None = None
    source_sha: str | None = None
    remote_state: str = "unknown"
    remote_stage: str | None = None
    remote_revision: str | None = None
    heartbeat_seq: int | None = None
    controller_id: str | None = None
    controller_epoch: int | None = None
    lease_expires_at: float | None = None
    mode: str = "observer"
    latest_significant_event: dict | None = None
    latest_evidence_ref: str | None = None
    pending_question: dict | None = None
    argus_project_id: str | None = None
    argus_status: str = "unbound"
    reviewer_verdict: str | None = None
    paused: bool = False
    events: dict = field(default_factory=dict)
    intent: dict | None = None
    decision_receipts: list = field(default_factory=list)
    max_attempts: int = 3
    submitted_attempts: int = 0
    failures: int = 0
    next_poll_at: float = 0
    last_seen: float | None = None
    material: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    schema_version: int = 1

    def to_dict(self):
        return asdict(self)


class SupervisorError(RuntimeError):
    """Only stable, non-secret codes cross API/log boundaries."""


class Unsupported(SupervisorError):
    pass


class AmbiguousMutation(SupervisorError):
    pass
