# Argus Supervisor (Face A)

Native OpenOperator profile and plugin for supervising **remote** OpenTraining
campaigns. Argus owns campaign decisions; Foreman is a bounded evidence sentinel.
Neither this plugin nor Foreman runs Training Master, Colab or Kaggle locally.
The governing specification is [here](../../docs/argus/openoperator_argus_supervisor_spec.md).

The plugin is discoverable by the existing loader but external work is disabled
until `ARGUS_SUPERVISOR_ENABLED=1`. It uses the existing authenticated HTTP service,
startup migration, job loop and DeferredTask owner. No extra listener is started.
The explicit unprefixed plugin name is required by the implementation contract.

## Configuration

Set through environment/Space secrets, never chat task text or tracked files:

| Variable | Meaning/default |
| --- | --- |
| `ARGUS_SUPERVISOR_ENABLED` | `0`; opt in with `1` |
| `OPENTRAINING_A2A_URL` | HTTPS A2A base, such as `https://service.example/a2a`; **no embedded token** |
| `OPENTRAINING_A2A_TOKEN` | Secret; sent as Bearer and X-API-KEY, never to model processes |
| `OPENTRAINING_A2A_PROJECT` | Optional project metadata; remote must support project selection |
| `ARGUS_SUPERVISOR_CONTROLLER_ID` | `argus-openoperator` |
| `ARGUS_SUPERVISOR_HEARTBEAT_SECONDS` | `120`; minimum 60, rounded up by the existing 60-second job-loop cadence |
| `ARGUS_SUPERVISOR_LEASE_TTL_SECONDS` | `600`; bounded 60–3600 |
| `ARGUS_SUPERVISOR_STATE_ROOT` | `/a0/usr/argus-supervisor` |
| `ARGUS_SUPERVISOR_ARGUS_HOME` | `<state root>/argus-home`; must stay under state root |
| `ARGUS_SUPERVISOR_ARGUS_PYTHON` | `/opt/venv-argus/bin/python` |
| `ARGUS_SUPERVISOR_BACKEND` | Required for model decisions; upstream-supported CLI backend, e.g. `codex`; no inferred default |
| `ARGUS_SUPERVISOR_FOREMAN_ENABLED` | `0`; advisory opt in with `1` |
| `ARGUS_SUPERVISOR_FOREMAN_PYTHON` | `/opt/venv-foreman/bin/python` |

Argus is installed at a source SHA into `/opt/argus` and `/opt/venv-argus`;
Foreman into `/opt/foreman` and `/opt/venv-foreman`. `runtime/source-lock.json`
records exact sources; constraint files pin qualified dependencies. The existing
framework venv is untouched by these installers. No runtime installation or sudo.
Argus's `argus` executable exists, but it can launch a cockpit: the bridge instead
calls the pinned Python API (`MemoryBundle`, upstream Manager and LifeSupervisor)
and pure CLI for operator answers. It never starts Argus's Web server or TUI.

Backend/model/credential configuration comes from the supported upstream
`ARGUS_SKILL_*` environment and the selected provider CLI. Configure that backend
before enabling autonomous decisions. Agent Zero's chat-model settings do not
implicitly configure Argus. Model decisions are finite, with a 120-second process
budget and two-round cap; timeout leaves a durable Needs you receipt, not a replay.
Argus logs/state live under its persistent home, not `/opt`.

Foreman uses upstream `JevForemanModel`, `FactoryObservation`, responsibility
registry and `FactoryPolicy`. Configure `TYPESAFE_API_KEY` and the matching
`TYPESAFE_BASE_URL` per upstream documentation (or the provider default).
Only completion, verification, worker health and human escalation are selected;
repository-instruction checks are not invented for an unseen remote repository.
`START_WORKER`, an additional upstream directive, becomes a `STEER_WORKER` planning
hint. No directive has a direct mutation path. FINISH is only candidate completion.
An unavailable sentinel does not block Argus or existing remote execution.

## Native API and workflow

All routes are authenticated POSTs with the existing session/CSRF rules:

- `/api/plugins/argus_supervisor/health`: runtime presence, configured booleans,
  pins, last tick and discovered logical capabilities; no credentials/endpoint URL.
- `/api/plugins/argus_supervisor/status`: compact campaigns and visible events.
- `/api/plugins/argus_supervisor/campaigns`: list/get; `action=create` with
  `campaign_id`, `objective`, optional `remote_task_id`, `max_attempts` (default 3,
  bounded 1–20). An attached remote task is never resubmitted.
- `/api/plugins/argus_supervisor/campaign_action`: `campaign_id`, `action`, arguments.
  Actions: observe, mission, claim, release, pause, resume, submit, intervene,
  cancel, answer, resolve_intent. `epoch` is mandatory for remote mutations except
  an explicit claim. Submit takes `text`; intervene `instruction`; cancel `reason`.

Create/attach → observe → mission (bind real Argus project) → explicitly claim if
remote capabilities support it. Claim never happens implicitly. Most ticks read
compact status only. Revision, stdout, cursor and routine metrics alone do not
wake either model. Significant events use a durable deduplicated outbox. Pure
EVIDENCE_READY with Foreman CONTINUE is retained without waking Argus.

State transitions, blockers, attempt outcomes, evidence and control changes can
wake Argus. Only Needs you, attempt outcomes, stage transitions, mission completion
and critical infrastructure/control loss are returned as public events. APIs
return retained event IDs for consumer deduplication; the job loop never injects
chat messages. There is no new WebUI panel or notification spam.

Every action needs fresh remote readback, a matching unexpired controller epoch,
and advertised remote epoch/policy enforcement. Argus proposals additionally need a fresh independent
Reviewer verdict tied to that event; old reviews and Foreman FINISH cannot authorize
an action. Approved decision IDs are consumed durably before relay. The adapter
adds authority outside task text, never accepts a model-provided epoch or task ID,
and limits submissions to the campaign's configured attempt bound.

A human API action is explicit authenticated operator control. Argus unavailable
means no autonomous proposals are executed; observations continue. Pause stops
polling/renewal; the remote lease expires unless the operator releases first.
Resume only observes/readbacks; it does not claim a lease.

A mutation intent is saved **before** network I/O. Any ambiguous response or
interruption retains it, drops local control and blocks replay. `resolve_intent`
requires authoritative remote request-ID readback (`applied`/`not_applied`) and
never resends or reacquires. If that operation is unsupported, keep observing and
reconcile manually at the remote service. Never delete the journal to force retry.
Interrupted Argus turns also remain durably ambiguous; inspect its local receipt
and upstream backlog rather than replaying the same event. A new operator answer
or new significant event can request another finite decision boundary.

## Remote compatibility contract

See [the wire contract](../../docs/argus/a2a-compatibility.md). Standard A2A is
sufficient for tentative `message/send`, `tasks/get` and task evidence; every
mutation is still prohibited without an advertised and verified lease extension.
Skill prose never grants authority. Unsupported methods are reported explicitly.
No remote source is modified by this implementation.

## Recovery and validation

Campaign JSON is the atomic authority for event outbox, remote IDs, lease snapshot,
mission binding, mutation intent and consumed decisions. Separate lease JSON and
event JSONL are diagnostic projections. Nonblocking file locks serialize campaign
transactions across processes and framework/API threads. Corruption fails closed;
it is not silently replaced. Read failures back off to 30 minutes and surface one
critical event at three consecutive failures; they do not invent a failed attempt.

Startup verifies bindings through the real runtime and rechecks remote state and
leases. Local journal ownership alone is insufficient; no startup claim or submit.
Foreman has no execution dependency on the A2A client. Argus/Foreman receive bounded,
redacted UNTRUSTED_REMOTE_DATA envelopes and no OpenTraining credentials. Raw Argus
traces stay in its private local home. This is process/dependency isolation, not an
OS sandbox for a separately configured trusted backend CLI.

Run the framework tests with `python -m pytest plugins/argus_supervisor/tests -q`.
To include real isolated package contracts, set `ARGUS_TEST_ARGUS_PYTHON` and
`ARGUS_TEST_FOREMAN_PYTHON`; without those, those two checks explicitly skip. CI
installs the pinned environments and selects them. Fake endpoint tests use real
loopback HTTP; no model/provider key is required. Follow the qualification report
for live release checks. Heartbeat does not prevent Hugging Face platform sleep.
