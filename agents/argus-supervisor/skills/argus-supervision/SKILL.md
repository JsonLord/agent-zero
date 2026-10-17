---
name: argus-supervision
description: Observe and control durable remote campaigns through the Argus Supervisor plugin.
---
Use authenticated POST `/api/plugins/argus_supervisor/status`, `campaigns`,
`campaign_action`, and `health` through the existing OpenOperator service/session.
Never start another server or read `.env` into model context.

`campaigns` accepts `action=create`, `campaign_id`, `objective`, and optional
`remote_task_id` to attach read-only. Otherwise it lists compact campaigns.
`campaign_action` accepts `campaign_id`, `action` and bounded action parameters.
Supported actions: observe, mission, claim, release, pause, resume, submit,
intervene, cancel, resolve_intent, answer. `claim` is explicit takeover, never
implicit on restart. `epoch` is mandatory for submit/intervene/cancel/release.
Resolve ambiguous intents only by authoritative remote request-ID readback, or
retain Needs you; never clear a timeout just to resend. Mission creation requires
a configured supported Argus backend. Backend setup remains operator-owned.
Show only significant public events and pending questions; do not narrate polling.
