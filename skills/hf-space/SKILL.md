---
name: hf-space
description: Prepare and validate a least-privilege Hugging Face Space deployment.
version: 1.0.0
tags: [engineering, openoperator]
---

# hf-space

## Classification

- **Agent Zero capability:** native workflow/instruction skill with repository smoke tooling.
- **Native executable:** `scripts/smoke_hf_openoperator.py` for non-destructive authenticated acceptance checks.
- **External dependency:** a reachable Hugging Face Space and credentials supplied only through documented environment variables.

Inspect Docker SDK metadata, port 7860, entrypoint, non-root ownership, writable runtime paths, health, production classification, masked secrets, settings persistence, and chat. Use `scripts/smoke_hf_openoperator.py` for its supported checks rather than claiming unobserved live results. The smoke utility validates a deployment; it does not deploy one. Provider or deployment writes require explicit approval and remain outside this skill's native executable capability. Read `HF_TOKEN` only from the environment, never print it, and report unavailable access as blocked.
