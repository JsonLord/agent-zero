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

Inspect `scripts/colab_a0.py` and use its supported start-or-reuse, health, `exec`, and stop operations exactly as implemented. After checking out the exact repository commit in Colab, run an argv command with `exec -- <program> <args>`; the helper returns bounded stdout/stderr tails and a structured evidence manifest. PASS requires exit code zero. Prefer local execution for trivial work. Discover Colab availability only when requested, report unavailable credentials as blocked rather than passed, and never expose tokens.
