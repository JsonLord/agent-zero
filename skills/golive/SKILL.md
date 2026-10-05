---
name: golive
description: Plan and safely execute production delivery with explicit approval gates.
version: 1.0.0
tags: [engineering, openoperator]
---

# golive

Adapted from mikehasa/golive-skill (MIT). Follow detect -> plan -> human approval -> apply -> verify -> status -> handoff. Never perform provider writes without a reviewed plan identifier and explicit confirmation. Dangerous DNS, destruction, live payments, spend, and teardown require separate confirmation. Secrets never enter argv, plans, state, reports, logs, or errors. Use a separately installed and verified upstream CLI only when available; never install or execute it at Agent Zero startup. If unavailable, stop at a deployment plan. Teardown applies only to resources proven created by the run.
