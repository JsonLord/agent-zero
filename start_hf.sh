#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
CLONE_DIR="/home/user/app/agent-zero-clone"
APP_DIR="/home/user/app"
PATCHES_DIR="/home/user/app/patches"

echo "Cloning Agent-Zero (main branch) into temporary directory..."
if [ -d "$CLONE_DIR" ]; then
    rm -rf "$CLONE_DIR"
fi

git clone "$REPO_URL" "$CLONE_DIR"

echo "Applying Agent-Zero codebase to app directory..."
cp -rn "$CLONE_DIR"/* "$APP_DIR/" 2>/dev/null || true

echo "Applying patches from $PATCHES_DIR..."
if [ -d "$PATCHES_DIR/helpers" ]; then
    cp -f "$PATCHES_DIR/helpers/"*.py "$APP_DIR/helpers/"
fi
if [ -d "$PATCHES_DIR/api" ]; then
    mkdir -p "$APP_DIR/api"
    cp -f "$PATCHES_DIR/api/"*.py "$APP_DIR/api/"
fi

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
