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
- `mode=internal`: the helper verified the named existing Agent Zero profile through the API, created a fresh context, submitted the stripped message asynchronously, polled it, and returned its result. Never create a profile in response to routing.
- Unknown `/sdk` names fail instead of falling back.
- Do not accept or construct endpoints from arbitrary URLs in user text; endpoints come only from environment registration.

## Durable goals and polling

Use `scripts/spynel_dispatch.py --goal '@developer <objective>'` for multi-step outcomes; omit `--goal` for one bounded operation. Goal mode calls the API-key-protected internal goal delegate and validates the profile before context creation. When retrying one submission after a transport failure, the caller may supply the same stable `--request-id` and optional `--request-scope`; without a caller ID, identical text intentionally creates an independent goal. External registered routes explicitly return `goal_unsupported` because they do not implement Agent Zero's goal protocol.

The dispatcher stores the accepted context/goal IDs, backs off between unchanged progress revisions up to `SPYNEL_MAX_POLL_INTERVAL`, resets on semantic progress, returns immediately for `requires_attention`, and never resubmits merely because work remains active.
