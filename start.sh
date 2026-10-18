#!/bin/bash

echo "Starting application..."

# Sync BLABLADOR_API_KEY to OTHER_API_KEY for Agent-Zero fallback
if [ -n "$BLABLADOR_API_KEY" ]; then
    export OTHER_API_KEY="$BLABLADOR_API_KEY"
    echo "BLABLADOR_API_KEY synced to OTHER_API_KEY"
fi

python run_ui.py --host 0.0.0.0 --port 7860 --dockerized=true
