#!/bin/bash
set -e

# install playwright - moved to install A0
# bash /ins/install_playwright.sh "$@"

# searxng - moved to base image
# bash /ins/install_searxng.sh "$@"

# Install mermaid-cli
bash /app/docker/run/fs/ins/install_mermaid.sh

# Install todo.ai
bash /app/docker/run/fs/ins/install_todo_ai.sh

# Install swarmtask
bash /app/docker/run/fs/ins/install_swarmtask.sh
