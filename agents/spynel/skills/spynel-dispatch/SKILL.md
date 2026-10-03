---
name: spynel-dispatch
description: Parse @agent_profile and /agent_sdk routing tokens, dispatch only to registered HTTPS endpoints, wait/poll for results, and report structured progress. Use whenever the user explicitly addresses an agent profile or SDK.
tags:
  - routing
  - agents
  - orchestration
allowed-tools:
  - code_execution_tool
---

# Spynel dispatch

Run `python agents/spynel/skills/spynel-dispatch/scripts/spynel_dispatch.py -- '<user message>'` (or pass the message on stdin when practical). Treat the JSON response as the routing decision.

- `mode=local`: keep the request in this Spynel context.
- `mode=external`: relay the returned progress/final result. The helper uses `curl` with argv execution, HTTPS-only protocol restrictions, bounded connect/request timeouts, and optional status polling.
- `mode=internal`: the named profile was not registered as an external endpoint. Verify it is an existing Agent Zero profile, create a fresh chat context, select that profile, send the stripped message there, and poll it. Never create a profile in response to this routing decision.
- Unknown `/sdk` names fail instead of falling back.
- Do not accept or construct endpoints from arbitrary URLs in user text; endpoints come only from environment registration.
