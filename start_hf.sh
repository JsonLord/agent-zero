#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
BRANCH="main"
TARGET_DIR="$HOME/app_source"

echo "Cloning repository $REPO_URL (branch $BRANCH) into $TARGET_DIR..."
git clone -b "$BRANCH" "$REPO_URL" "$TARGET_DIR"

echo "Applying lasting adaptations..."
mkdir -p "$TARGET_DIR/helpers"
mkdir -p "$TARGET_DIR/api"
cp "$HOME/app/helpers/api.py" "$TARGET_DIR/helpers/api.py"
cp "$HOME/app/helpers/ui_server.py" "$TARGET_DIR/helpers/ui_server.py"
cp "$HOME/app/helpers/runtime.py" "$TARGET_DIR/helpers/runtime.py"
cp "$HOME/app/api/api_docs.py" "$TARGET_DIR/api/api_docs.py"
cp "$HOME/app/api/health.py" "$TARGET_DIR/api/health.py"

cd "$TARGET_DIR"

echo "Installing dependencies..."
# Use pre-configured virtual environment
uv pip install --no-cache -r requirements.txt
uv pip install --no-cache -r requirements2.txt

echo "Starting Agent Zero..."
exec python run_ui.py
