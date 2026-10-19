#!/usr/bin/env bash
set -euo pipefail
# Alternative source launcher. Docker deployments use start_openoperator.sh instead.
REPO_URL="https://github.com/JsonLord/agent-zero.git"
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${OPENTRAINING_SOURCE_REF:=opentraining}"
# Execute a fresh checkout rather than overlaying Space files. Persistent state stays
# in the original app directory, including Training Master configuration/experiments.
SOURCE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/opentraining-source.XXXXXXXX")"
git -C "$SOURCE_DIR" init --quiet
git -C "$SOURCE_DIR" remote add origin "$REPO_URL"
git -C "$SOURCE_DIR" fetch --quiet --depth 1 origin "$OPENTRAINING_SOURCE_REF"
git -C "$SOURCE_DIR" checkout --quiet --detach FETCH_HEAD
SOURCE_SHA="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
printf 'OpenTraining source SHA: %s\n' "$SOURCE_SHA"
for state in usr logs tmp per; do
    mkdir -p "$APP_DIR/$state"
    # A source tree must never replace persistent state with tracked files.
    if [[ -e "$SOURCE_DIR/$state" ]]; then
        mv "$SOURCE_DIR/$state" "$SOURCE_DIR/.source-skeleton-$state"
    fi
    ln -s "$APP_DIR/$state" "$SOURCE_DIR/$state"
done
cd "$SOURCE_DIR"
# This identity comes from the actual fetched checkout, not the requested ref name.
export OPENTRAINING_FETCHED_SHA="$SOURCE_SHA"
python - <<'PYTHON'
import json
import os
from pathlib import Path
Path('opentraining-build.json').write_text(json.dumps({'source_sha': os.environ['OPENTRAINING_FETCHED_SHA']}))
PYTHON
# No patch overlay: helpers/ui_server.py is the canonical runtime implementation.
if command -v uv >/dev/null; then
    uv pip install --system --no-cache -r requirements.txt
else
    python -m pip install --no-cache-dir -r requirements.txt
fi
export HF_SPACE=true PORT=7860 HOST=0.0.0.0
python scripts/configure_hf_a2a.py --app-root "$SOURCE_DIR"
exec python run_ui.py --host=0.0.0.0 --port=7860
