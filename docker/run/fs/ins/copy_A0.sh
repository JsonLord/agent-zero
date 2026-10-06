#!/bin/bash
set -e

# Paths
SOURCE_DIR="/git/agent-zero"
TARGET_DIR="/a0"

# Deterministically synchronize application code while excluding persistent user state (/a0/usr)
if [ -d "$SOURCE_DIR" ]; then
    echo "Synchronizing application code from $SOURCE_DIR to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    rsync -a --no-owner --no-group --exclude='/usr' "$SOURCE_DIR/" "$TARGET_DIR/"
fi