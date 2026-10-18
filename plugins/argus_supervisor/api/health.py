import os
from pathlib import Path

from helpers.api import ApiHandler, Request
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.argus_bridge import ARGUS_PIN
from plugins.argus_supervisor.helpers.foreman_bridge import FOREMAN_PIN


def health_status() -> dict:
    argus = os.getenv("ARGUS_SUPERVISOR_ARGUS_PYTHON", "/opt/venv-argus/bin/python")
    foreman = os.getenv(
        "ARGUS_SUPERVISOR_FOREMAN_PYTHON", "/opt/venv-foreman/bin/python"
    )
    return {
        "enabled": service.enabled(),
        "argus_pin": ARGUS_PIN,
        "foreman_pin": FOREMAN_PIN,
        "argus_executable_present": Path(argus).is_file(),
        "foreman_executable_present": Path(foreman).is_file(),
        "backend_configured": bool(os.getenv("ARGUS_SUPERVISOR_BACKEND")),
        "a2a_token_present": bool(os.getenv("OPENTRAINING_A2A_TOKEN")),
        "endpoint_configured": bool(os.getenv("OPENTRAINING_A2A_URL")),
        "last_tick": service._instance.last_tick if service._instance else None,
        "capabilities": service._instance.capabilities if service._instance else {},
        "listener": "existing_agent_zero_only",
    }

class Health(ApiHandler):
    async def process(self, input: dict, request: Request):
        return health_status()
