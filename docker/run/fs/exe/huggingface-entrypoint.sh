#!/bin/bash
set -euo pipefail

# Hugging Face provides the public HTTPS edge; never start an outbound tunnel.
if [ "${A0_CLOUDFLARE_DISABLED:-true}" != "true" ]; then
    echo "A0_CLOUDFLARE_DISABLED must remain true on Hugging Face Spaces." >&2
    exit 1
fi

mkdir -p /a0/usr

# Settings normalization fills all other defaults. This deployment default makes
# the authenticated A2A endpoint available immediately after the Space starts.
python3 - <<'PY'
import json
from pathlib import Path

settings_path = Path("/a0/usr/settings.json")
try:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

settings["a2a_server_enabled"] = True
settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY

echo "Space URL: ${A0_PUBLIC_URL:-https://leon4gr45-agent.hf.space}"
echo "A2A enabled at /a2a; authenticated incoming API enabled at /api/api_message."
exec /exe/initialize.sh "${BRANCH:-local}"
