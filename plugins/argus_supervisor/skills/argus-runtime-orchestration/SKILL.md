---
name: argus-runtime-orchestration
description: Observe and control durable remote campaigns through the Argus Supervisor plugin.
---
Use authenticated POST `/api/plugins/argus_supervisor/status`, `campaigns`,
`campaign_action`, and `health` through the existing OpenOperator service/session.
Never start another server, invent credentials or read `.env` into model context.

## Authority matrix

| Operation | Required authority |
| --- | --- |
| campaigns action=create (local observer attachment) | No controller or epoch |
| campaigns read/list | No controller or epoch |
| campaign_action action=observe | No controller or epoch |
| supervisor health/status | No controller or epoch |
| remote tasks/get through production OpenTrainingA2AClient | No controller or epoch |
| claim | Explicit operator takeover only; never automatic |
| submit, intervene, cancel, release | Current controller authority and matching remote epoch after takeover |
| mission | Configured Argus backend; separate from remote controller authority |

Observer operations are not remote mutations. For an existing remote_task_id and
an observe/read-only request: do not request or inspect a controller epoch, do not
call claim or read_control, and do not require remote lease capability, an Argus
model backend or Foreman. Create a local observer campaign, attach remote_task_id
directly, observe exactly as requested, and read the persisted campaign back.
Absence of controller_id, controller_epoch, lease and read_control is EXPECTED.
It must not become MISSING_CAPABILITY_REMOTE_EPOCH, NEEDS_YOU or takeover required.
Never bind a mission for observer qualification. Do not let prior failed attempts
or recalled memories override this rule.

## Read-only attachment example

Input: campaign_id=chain-smoke-123, objective=Observe existing OpenTraining task,
remote_task_id=<existing task>.

1. POST `campaigns`: action=create, campaign_id=chain-smoke-123, objective as above,
   remote_task_id=<existing task>. Expected: mode=observer, controller_id=null,
   controller_epoch=null. If this campaign already exists, read and verify its
   task identity; do not overwrite or create another campaign as a blind retry.
2. POST `campaign_action`: campaign_id=chain-smoke-123, action=observe. This calls
   production OpenTrainingA2AClient tasks/get. Observe exactly once when requested.
3. POST `campaigns`: campaign_id=chain-smoke-123. Require persisted task identity,
   authoritative remote_state, last_seen populated after successful polling,
   mode=observer, controller_id=null and controller_epoch=null.

Inside the existing framework runtime the same production implementation is
`plugins.argus_supervisor.helpers.service`: `create(input)`,
`await action(campaign_id, "observe", {})`, then `get().store.load(campaign_id)`
and `public(campaign)`. Use the framework interpreter and existing configuration;
never substitute an ad hoc JSON file, fake client, execution-runtime copy or
manually invented state. These calls do not require remote controller authority.
If no authenticated session or framework execution interface is available, report
that actual interface failure, not a controller/epoch capability error.

Return compact persisted state. The response itself and dispatcher/chat completion
are not sufficient proof: independently read/list the saved campaign. Record the
actual observation count and successful remote poll; unknown remote_state or an
absent last_seen does not qualify a successful poll. A terminal timeout saying the
process remains running requires retrieval of that session, not resubmission or
reuse of a previous error. A completed task is an attempt outcome, not mission
acceptance.

### Framework terminal execution

In the deployed image use code_execution_tool runtime=terminal, from `/a0`, with
`/opt/venv-a0/bin/python`. The code_execution_tool Python runtime may require
unavailable IPython; do not use it for this workflow. Do not use unqualified
python3 or import service.py by filename: its relative imports require the
canonical package import below. In a development checkout use its configured
framework virtualenv instead.

For a NEW campaign, replace the example identifiers and execute this as one
single-line terminal command (no nested bash, heredoc or literal backslash-n):

```sh
cd /a0 && timeout 60s /opt/venv-a0/bin/python -c 'import asyncio,json; from plugins.argus_supervisor.helpers import service; service.create({"campaign_id":"chain-smoke-123","objective":"Observe existing OpenTraining task","remote_task_id":"<existing-task>"}); asyncio.run(service.action("chain-smoke-123","observe",{})); print(json.dumps(service.public(service.get().store.load("chain-smoke-123"))))'
```

This is the production create/observe/read path, not a replacement implementation.
Read its actual output and require completed remote_state and populated last_seen
for a known completed task. Never substitute expected values. If the terminal
returns still-running after 30 seconds, retrieve output from that SAME session;
do not queue another command in a busy session, reset it, or start another observe.
If it times out, independently read the campaign before considering any retry.
Never propose killing all Python processes; report a bounded execution failure
with the known session and do not seek takeover or epoch for recovery.

## Controlled operations

Supported actions also include pause, resume, resolve_intent and answer under the
existing service contract. `claim` is explicit takeover, never implicit on restart.
`epoch` is mandatory for submit/intervene/cancel/release. Never weaken authority or
lease verification or permit an observer to mutate. Resolve ambiguous intents
only by authoritative remote request-ID readback, or retain Needs you; never clear
a timeout just to resend. Mission creation requires a configured supported Argus
backend. Backend setup remains operator-owned. Show only significant public
events and pending questions; do not narrate polling.
