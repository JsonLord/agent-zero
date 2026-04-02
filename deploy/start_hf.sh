#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
CLONE_DIR="/home/user/app/agent-zero-clone"
APP_DIR="/home/user/app"

echo "Cloning Agent-Zero (fix-a2a-auth-15797037665282663574 branch)..."
if [ -d "$CLONE_DIR" ]; then
    rm -rf "$CLONE_DIR"
fi

git clone --branch fix-a2a-auth-15797037665282663574 "$REPO_URL" "$CLONE_DIR"

echo "Applying adaptations..."
cp -rn "$CLONE_DIR"/* "$APP_DIR/" 2>/dev/null || true

cp -f /home/user/app/helpers/api.py "$APP_DIR/python/helpers/api.py"
cp -f /home/user/app/helpers/runtime.py "$APP_DIR/python/helpers/runtime.py"
cp -f /home/user/app/helpers/settings.py "$APP_DIR/python/helpers/settings.py"
cp -f /home/user/app/run_ui.py "$APP_DIR/run_ui.py"
cp -f /home/user/app/api/api_docs.py "$APP_DIR/python/api/api_docs.py"

if [ -f "/home/user/app/helpers/ws.py" ]; then
    cp -f /home/user/app/helpers/ws.py "$APP_DIR/python/helpers/ws.py"
fi

echo "Installing dependencies..."
if command -v uv > /dev/null; then
    uv pip install --system --no-cache -r "$APP_DIR/requirements.txt"
    uv pip install --system flask-socketio eventlet
else
    pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
    pip install flask-socketio eventlet
fi

export HF_SPACE=true
export PORT=7860
export HOST=0.0.0.0

echo "Starting Agent-Zero..."
python run_ui.py --host 0.0.0.0 --port 7860 --dockerized=true
