---
name: colab-execute
description: Use the existing Colab Agent Zero lifecycle for dependency-heavy isolated execution.
version: 1.0.0
tags: [engineering, openoperator]
---

# colab-execute

## Classification

- **Agent Zero capability:** workflow/instruction skill backed by a native repository executable.
- **Native executable:** `scripts/colab_a0.py`, the canonical Colab Agent Zero lifecycle helper.
- **External dependency:** an available Colab runtime and its credentials; neither is required at Agent Zero startup.

Inspect `scripts/colab_a0.py` and use its supported start-or-reuse, health, and stop operations exactly as implemented. The helper manages the Agent Zero lifecycle; it does not itself replace the test runner, so execute tests separately inside the notebook or runtime. Collect commit, Python version, commands, exit codes, passed/failed/skipped/blocked counts, and artifact paths. Prefer local execution for trivial work. Discover Colab availability only when requested, report unavailable credentials as blocked rather than passed, and never expose tokens.
