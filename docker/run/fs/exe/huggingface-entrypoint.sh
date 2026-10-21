#!/bin/bash
set -euo pipefail

# Hugging Face provides the public HTTPS edge; never start an outbound tunnel.
if [ "${A0_CLOUDFLARE_DISABLED:-true}" != "true" ]; then
    echo "A0_CLOUDFLARE_DISABLED must remain true on Hugging Face Spaces." >&2
    exit 1
fi

bash /ins/copy_A0.sh
mkdir -p /a0/usr

# Settings normalization fills all other defaults. This deployment default makes
# the authenticated A2A endpoint available immediately after the Space starts.
python3 - <<'PY'
import json
import os
from pathlib import Path

settings_path = Path("/a0/usr/settings.json")
try:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

external_enabled = bool(os.getenv("SPYNEL_AGENT_ZERO_API_KEY", "").strip())
settings["a2a_server_enabled"] = external_enabled
settings["mcp_server_enabled"] = external_enabled
if external_enabled:
    print("MCP, A2A and incoming API enabled using the deployment secret.")
else:
    print("External integrations disabled: SPYNEL_AGENT_ZERO_API_KEY is not configured.")
settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY

echo "Space URL: ${A0_PUBLIC_URL:-https://leon4gr45-openoperator.hf.space}"
echo "External endpoints share port 7860; browser authentication and CSRF remain required."

# Safe Argus diagnostic
argus_enabled="false"
if [ "${ARGUS_SUPERVISOR_ENABLED:-0}" = "1" ]; then
  argus_enabled="true"
fi
argus_runtime_present="false"
if [ -x "/opt/venv-argus/bin/python" ]; then
  argus_runtime_present="true"
fi
argus_backend_configured="false"
if [ -n "${ARGUS_SUPERVISOR_BACKEND:-}" ]; then
  argus_backend_configured="true"
fi
echo "Argus Supervisor: enabled=$argus_enabled runtime_present=$argus_runtime_present backend_configured=$argus_backend_configured"

echo "Starting Agent Zero as uid=$(id -u) on ${WEB_UI_HOST:-0.0.0.0}:${WEB_UI_PORT:-7860}."
echo "Runtime mode: dockerized production"

# The general Docker initializer is intentionally not used in a Space: it starts
# privileged SSH/cron/supervisor services and inherited images may include
# password initialization. Space dependencies and model data are installed at
# image-build time, so runtime package installation is disabled by the image.
cd /a0
/opt/venv-a0/bin/python -m helpers.hf_space_defaults
exec /opt/venv-a0/bin/python /exe/huggingface-services.py
