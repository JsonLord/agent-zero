#!/usr/bin/env bash
set -euo pipefail

export TRAINING_MASTER_VENV="${TRAINING_MASTER_VENV:-/opt/venv-training-master}"
export TRAINING_MASTER_PYTHON_BIN="${TRAINING_MASTER_PYTHON_BIN:-${TRAINING_MASTER_VENV}/bin/python}"
export TRAINING_MASTER_STATE_DIR="${TRAINING_MASTER_STATE_DIR:-/a0/usr/training-master}"

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-/a0/usr/config}"
export GH_CONFIG_DIR="${GH_CONFIG_DIR:-/a0/usr/config/gh}"
export KAGGLE_CONFIG_DIR="${KAGGLE_CONFIG_DIR:-/a0/usr/config/kaggle}"

mkdir -p \
    "${TRAINING_MASTER_STATE_DIR}/jobs" \
    "${TRAINING_MASTER_STATE_DIR}/experiments" \
    "${TRAINING_MASTER_STATE_DIR}/logs" \
    "${TRAINING_MASTER_STATE_DIR}/indexes" \
    /a0/usr/config/colab-cli \
    /a0/usr/config/kaggle \
    /a0/usr/config/gh \
    /a0/usr/cache/huggingface \
    /a0/usr/cache/uv \
    /a0/usr/supervisor

# IMPORTANT:
# Never launch OAuth flows automatically from service startup.
# Agent Zero may use authenticated CLIs but login remains a human operation.
training-master-doctor
