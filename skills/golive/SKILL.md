---
name: golive
description: Plan and safely execute production delivery with explicit approval gates.
version: 1.0.0
tags: [engineering, openoperator]
---

# golive

## Classification

- **Agent Zero capability:** workflow/instruction skill and external-tool adapter.
- **Not bundled:** the `mikehasa/golive-skill` runtime or a native deployment executable.
- **Optional dependency:** a separately installed, trusted, and verified upstream GoLive CLI.

Adapted from `mikehasa/golive-skill` (MIT). Follow detect -> plan -> human approval -> apply -> verify -> status -> handoff. The built-in capability can inspect, prepare a deployment plan, define verification, and report readiness. Provider mutations require the optional upstream tool or another explicitly approved provider mechanism.

Never perform provider writes without a reviewed plan identifier and explicit human confirmation. Dangerous DNS changes, destruction, live payments, spend, and teardown require separate confirmation. High goal autonomy never grants production approval. Secrets never enter argv, plans, state, reports, logs, or errors. Discover the optional CLI lazily when this skill is invoked; never install or execute it during Agent Zero startup. If it is unavailable, stop at a deployment plan and report the external operation as not executed. Teardown applies only to resources proven created by the run.
