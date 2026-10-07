---
name: huggingface-space-operator
description: OpenOperator Hugging Face Space lifecycle diagnosis, source SHA validation, and smoke verification.
---

# Hugging Face Space Operator Skill

## Capabilities

- Read `deployment.md` for OpenOperator Space contracts.
- Check source SHA via `GET /health` (`{"status": "ok", "sha": "<git-sha>"}`).
- Compare expected GitHub commit SHA against deployed Space SHA.
- Run `scripts/smoke_hf_openoperator.py` to verify profiles, skills, and Spynel routing.
