#!/bin/bash
set -e

REPO_URL="https://github.com/JsonLord/agent-zero.git"
CLONE_DIR="/home/user/app/agent-zero-clone"
APP_DIR="/home/user/app"
PATCHES_DIR="/home/user/app/patches"

echo "Ensuring uv is installed..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/user/.local/bin:$PATH"

echo "Cloning Agent-Zero (main branch)..."
if [ -d "$CLONE_DIR" ]; then rm -rf "$CLONE_DIR"; fi
git clone "$REPO_URL" "$CLONE_DIR"

echo "Applying codebase (overwriting existing files to ensure newest version)..."
# We use -f to overwrite, and we avoid copying the clone dir into itself if APP_DIR and CLONE_DIR are related
# In the Dockerfile, APP_DIR is /home/user/app.
cp -rf "$CLONE_DIR"/* "$APP_DIR/"

echo "Applying adaptations from $PATCHES_DIR..."
if [ -d "$PATCHES_DIR/helpers" ]; then
    mkdir -p "$APP_DIR/helpers"
    cp -vf "$PATCHES_DIR/helpers/"*.py "$APP_DIR/helpers/"
fi
if [ -d "$PATCHES_DIR/api" ]; then
    mkdir -p "$APP_DIR/api"
    cp -vf "$PATCHES_DIR/api/"*.py "$APP_DIR/api/"
fi

echo "Standardizing cloned codebase imports..."
# The main repo might use 'from python.helpers' if it was structured differently
find "$APP_DIR" -maxdepth 3 -name "*.py" -exec sed -i 's/from python\.helpers/from helpers/g' {} +
find "$APP_DIR" -maxdepth 3 -name "*.py" -exec sed -i 's/from python\.api/from api/g' {} +

echo "Installing dependencies..."
uv venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

# Install requirements from the cloned repo
uv pip install --no-cache -r "$APP_DIR/requirements.txt"

# Install our custom requirements if they exist (they should be in APP_DIR/requirements2.txt from the Docker COPY)
if [ -f "$APP_DIR/requirements2.txt" ]; then
    uv pip install --no-cache -r "$APP_DIR/requirements2.txt"
fi

export HF_SPACE=true
export PORT=7860
export HOST=0.0.0.0

echo "Starting Agent-Zero..."
python run_ui.py --host 0.0.0.0
