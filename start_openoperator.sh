#!/usr/bin/env bash
set -euo pipefail

echo "Starting OpenOperator Training Master bootstrap..."

# Prepare/verify the Training Master control plane.
# This never triggers OAuth.
init-training-master

# Keep the existing OpenOperator/Hugging Face startup script untouched.
UPSTREAM_INIT="/a0/docker/hf/initialize_hf.sh"

if [[ ! -f "$UPSTREAM_INIT" ]]; then
    echo "ERROR: expected OpenOperator startup script not found: $UPSTREAM_INIT" >&2
    echo "Repository contents under /a0/docker/hf:" >&2
    ls -la /a0/docker/hf 2>&1 || true
    exit 127
fi

echo "Handing off to existing OpenOperator startup: $UPSTREAM_INIT"

# exec preserves signals / exit status for the real application process.
exec bash "$UPSTREAM_INIT"
