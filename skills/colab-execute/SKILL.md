---
name: colab-execute
description: Use the existing Colab Agent Zero lifecycle for dependency-heavy isolated execution.
version: 1.0.0
tags: [engineering, openoperator]
---

# colab-execute

Inspect scripts/colab_a0.py. Use start or reuse, health, and stop exactly as implemented. The helper manages Agent Zero lifecycle; execute tests separately inside the notebook/runtime. Collect commit, Python, commands, exit codes, passed/failed/skipped/blocked, and artifact paths. Do not require Colab for trivial work and never expose tokens.
