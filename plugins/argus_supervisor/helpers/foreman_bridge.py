"""Advisory sentinel. This module has no remote client or mutation dependency."""

import os

from .runtime_bridge import invoke
from .security import evidence_envelope

FOREMAN_PIN = "381ca2de90af9efc2781a58055cc3028c7cabbb9"
HINTS = {
    "CONTINUE": "none",
    "START_VERIFIER": "review",
    "STEER_WORKER": "plan",
    "STOP_WORKER": "decision",
    "RETRY_WORKER": "plan",
    "FINISH": "candidate_completion",
    "ESCALATE": "needs_you",
}


class ForemanBridge:
    def __init__(self, home, python=None):
        self.home = home
        self.python = python or os.getenv(
            "ARGUS_SUPERVISOR_FOREMAN_PYTHON", "/opt/venv-foreman/bin/python"
        )

    async def verify(self):
        return await invoke(
            self.python,
            "foreman_worker.py",
            {"operation": "verify"},
            self.home,
            timeout=15,
            kind="foreman",
        )

    async def assess(self, campaign, evidence):
        result = await invoke(
            self.python,
            "foreman_worker.py",
            {
                "objective": campaign.objective,
                "run_id": campaign.run_id or campaign.campaign_id,
                "state": campaign.remote_state,
                "evidence": evidence_envelope(evidence),
            },
            self.home,
            timeout=30,
            kind="foreman",
        )
        directive = result.get("directive")
        if directive not in HINTS:
            return {"directive": "ESCALATE", "hint": "review"}
        return {"directive": directive, "hint": HINTS[directive]}
