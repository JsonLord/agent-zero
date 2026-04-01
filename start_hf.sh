#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
BRANCH="fix-a2a-auth-15797037665282663574"
TARGET_DIR="/a0"

echo "Cloning repository $REPO_URL (branch $BRANCH) into $TARGET_DIR..."
git clone -b "$BRANCH" "$REPO_URL" "$TARGET_DIR"

echo "Applying lasting adaptations..."
cp /app/helpers/api.py "$TARGET_DIR/helpers/api.py"
cp /app/helpers/ui_server.py "$TARGET_DIR/helpers/ui_server.py"
cp /app/helpers/runtime.py "$TARGET_DIR/helpers/runtime.py"

cd "$TARGET_DIR"

echo "Installing dependencies..."
uv pip install -r requirements.txt
uv pip install -r requirements2.txt

echo "Starting Agent Zero..."
exec python run_ui.py
