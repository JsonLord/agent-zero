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

settings["a2a_server_enabled"] = True
if api_key := os.environ.get("SPYNEL_AGENT_ZERO_API_KEY", "").strip():
    # Use one secret for the loopback client and the existing API-key verifier.
    # It is persisted in the private runtime settings file and never printed.
    settings["mcp_server_token"] = api_key
settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY

echo "Space URL: ${A0_PUBLIC_URL:-https://leon4gr45-openoperator.hf.space}"
echo "A2A enabled at /a2a; authenticated incoming API enabled at /api_message."
echo "Starting Agent Zero as uid=$(id -u) on ${WEB_UI_HOST:-0.0.0.0}:${WEB_UI_PORT:-7860}."

# The general Docker initializer is intentionally not used in a Space: it starts
# privileged SSH/cron/supervisor services and inherited images may include
# password initialization. Space dependencies and model data are installed at
# image-build time, so runtime package installation is disabled by the image.
cd /a0
/opt/venv-a0/bin/python -m helpers.hf_space_defaults || true
exec /opt/venv-a0/bin/python run_ui.py
