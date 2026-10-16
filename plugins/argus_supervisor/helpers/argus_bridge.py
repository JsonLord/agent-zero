"""Only significant boundaries enter the real, pinned Argus role pipeline."""

import os

from .models import SupervisorError
from .runtime_bridge import invoke
from .security import clean, evidence_envelope

ARGUS_PIN = "fdfeb715b0749db176c7d8b3212a717fb81087ba"


class ArgusBridge:
    def __init__(self, home, python=None, backend=None):
        self.home = home
        self.python = python or os.getenv(
            "ARGUS_SUPERVISOR_ARGUS_PYTHON", "/opt/venv-argus/bin/python"
        )
        self.backend = (
            backend
            if backend is not None
            else os.getenv("ARGUS_SUPERVISOR_BACKEND", "")
        )

    async def call(self, operation, campaign, **kwargs):
        return await invoke(
            self.python,
            "argus_worker.py",
            {
                "operation": operation,
                "campaign_id": campaign.campaign_id,
                "objective": campaign.objective,
                "backend": self.backend,
                **kwargs,
            },
            self.home,
        )

    async def verify(self):
        return await invoke(
            self.python, "argus_worker.py", {"operation": "verify"}, self.home
        )

    async def bind(self, campaign):
        result = await self.call("bind", campaign)
        campaign.argus_project_id = result["project_id"]
        campaign.argus_status = "observing"
        return result

    async def status(self, campaign):
        return await self.call("status", campaign)

    async def notify(self, campaign, events, evidence, hint):
        if not self.backend or self.backend == "memory":
            raise SupervisorError("argus_backend_not_configured")
        return await self.call(
            "event",
            campaign,
            events=[
                {
                    "id": e["id"],
                    "type": e["type"],
                    "revision": e.get("revision"),
                    "data": clean(e.get("data"), 600),
                }
                for e in events
            ],
            evidence=evidence_envelope(clean(evidence, 6000)),
            foreman_hint=hint,
        )

    async def answer(self, campaign, answer):
        return await self.call("answer", campaign, answer=answer)
