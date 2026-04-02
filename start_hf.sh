#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
CLONE_DIR="/home/user/app/agent-zero-clone"
APP_DIR="/home/user/app"

echo "Cloning Agent-Zero (main branch)..."
if [ -d "$CLONE_DIR" ]; then
    rm -rf "$CLONE_DIR"
fi

git clone "$REPO_URL" "$CLONE_DIR"

echo "Applying adaptations..."
cp -rn "$CLONE_DIR"/* "$APP_DIR/" 2>/dev/null || true

cp -f /home/user/app/helpers/api.py "$APP_DIR/helpers/api.py"
cp -f /home/user/app/helpers/runtime.py "$APP_DIR/helpers/runtime.py"
cp -f /home/user/app/helpers/settings.py "$APP_DIR/helpers/settings.py"
cp -f /home/user/app/helpers/ui_server.py "$APP_DIR/helpers/ui_server.py"
cp -f /home/user/app/api/api_docs.py "$APP_DIR/api/api_docs.py"

echo "Installing dependencies..."
if command -v uv > /dev/null; then
    uv pip install --system --no-cache -r "$APP_DIR/requirements.txt"
else
    pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
fi

export HF_SPACE=true
export PORT=7860
export HOST=0.0.0.0

echo "Starting Agent-Zero..."
python run_ui.py
