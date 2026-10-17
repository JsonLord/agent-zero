OpenOperator Argus Supervisor — Face A Specification
Target repository: `JsonLord/agent-zero`
Target branch: `jules-17409741302335967131-509964cf`
Scope: OpenOperator / Agent Zero adaptation only
Out of scope: LoopX integration, LoopX dashboard work, changes to OpenTraining internals, changes to Colab/Kaggle Training Master implementation
---
1. Objective
Adapt OpenOperator so it can host a durable Argus Supervisor that supervises long-running work executed by the separate OpenTraining service over authenticated A2A HTTPS.
The OpenOperator deployment becomes the autonomous cloud-facing control surface:
```text
User
  │
  ▼
OpenOperator / Agent Zero
  │
  ├─ Agent Profile: argus-supervisor
  │
  ├─ Plugin: argus_supervisor
  │    ├─ OpenTraining A2A client
  │    ├─ compact event reducer
  │    ├─ controller lease manager
  │    ├─ heartbeat worker
  │    ├─ Argus runtime bridge
  │    └─ Foreman evidence gate
  │
  ├─ isolated Argus runtime
  │
  └─ persistent supervisor state under /a0/usr
       │
       ▼
OpenTraining HTTPS A2A
       │
       ▼
Training Master / Git / Colab / Kaggle
```
OpenOperator must not become the training runtime. It supervises and controls OpenTraining, while OpenTraining owns Git/Training Master/Colab/Kaggle execution.
---
2. Governing Architecture
2.1 Authority hierarchy
There must be one clear hierarchy:
```text
Argus
  = campaign-level supervisor

Foreman
  = fast semantic evidence/intervention gate

OpenTraining
  = execution agent

Training Master
  = training-domain execution control

Colab/Kaggle/DGX
  = compute backends
```
Foreman must not become a competing campaign supervisor.
Argus owns:
mission objective;
campaign state;
stage transitions;
next-task planning;
repair strategy;
reviewer decisions;
operator escalation;
mission completion.
Foreman owns only bounded assessments such as:
worker health;
likely progress/stuckness;
evidence sufficiency;
verification need;
likely off-track behavior;
whether a full Argus review should be triggered.
OpenTraining owns:
repository mutation;
local development checks;
commit/push;
remote runtime invocation;
model/training execution;
attempt evidence collection.
2.2 No duplicate execution ownership
OpenOperator must never directly run Training Master locally as a substitute for OpenTraining.
Forbidden:
```text
OpenOperator → python Training_Master_Colab.py
OpenOperator → local Torch/Soup/PEFT training
OpenOperator → direct Colab execution bypassing OpenTraining
```
Required:
```text
OpenOperator
  → A2A
  → OpenTraining
  → Training Master
  → remote compute
```
---
3. Existing OpenOperator Capabilities to Reuse
The target Jules branch already contains relevant infrastructure. Reuse it instead of introducing parallel systems.
Expected existing surfaces include:
Agent Profiles under `agents/`;
plugin system under `plugins/`;
scheduler APIs and scheduler runtime;
A2A support through FastA2A helpers;
`helpers/fasta2a_client.py`;
`helpers/fasta2a_server.py`;
project-aware A2A behavior;
API token authority infrastructure;
`/a0/usr` persistent state;
immutable application/runtime separation;
HF Space deployment on port `7860`;
specialist profile conventions;
health/SHA deployment verification.
Do not replace these owners.
---
4. New OpenOperator Components
4.1 Agent Profile
Add:
```text
agents/argus-supervisor/
├── AGENTS.md
├── agent.yaml
├── prompts/
│   ├── agent.system.main.role.md
│   └── agent.system.main.specifics.md
└── skills/
    └── argus-supervision/
        └── SKILL.md
```
The profile is the human-facing facade for the supervisor.
It is not itself the Argus runtime.
Profile responsibilities:
show compact campaign state;
start/attach to a supervision mission;
request takeover/release;
expose significant events;
surface `Needs you` decisions;
show evidence summaries;
stop/resume supervision;
explain why Argus/Foreman made a decision.
The profile must not emit routine heartbeat chatter.
4.2 Plugin
Add:
```text
plugins/argus_supervisor/
├── plugin.yaml
├── README.md
├── default_config.yaml
├── helpers/
│   ├── a2a_client.py
│   ├── argus_bridge.py
│   ├── campaign_store.py
│   ├── event_reducer.py
│   ├── foreman_bridge.py
│   ├── heartbeat.py
│   ├── lease.py
│   ├── models.py
│   └── security.py
├── api/
│   ├── status.py
│   ├── campaigns.py
│   ├── campaign_action.py
│   └── health.py
├── extensions/
│   └── python/
│       └── <use an existing supported startup/runtime hook>
├── skills/
│   └── argus-runtime-orchestration/
│       └── SKILL.md
├── tests/
│   ├── test_a2a_client.py
│   ├── test_campaign_store.py
│   ├── test_event_reducer.py
│   ├── test_foreman_bridge.py
│   ├── test_heartbeat.py
│   ├── test_lease.py
│   └── test_security.py
└── webui/
    └── optional minimal supervisor status panel
```
Use actual plugin extension points already supported by the target branch. Do not invent a new plugin loader.
---
5. Runtime Isolation
5.1 Agent Zero runtime
Existing:
```text
/opt/venv-a0
```
Must remain immutable at runtime.
Never:
`chmod` it;
pip-install into it;
mutate its site-packages;
use it as Argus's Python environment.
5.2 Argus runtime
Install Argus at image build time into an isolated runtime, for example:
```text
/opt/argus
/opt/venv-argus
```
Recommended structure:
```text
/opt/argus/                source checkout or installed source snapshot
/opt/venv-argus/           Argus Python environment
/a0/usr/argus-supervisor/  persistent mutable state
```
Set Argus persistent state under:
```text
/a0/usr/argus-supervisor/argus-home
```
Do not write mutable Argus state into `/opt`.
5.3 Foreman runtime
Prefer one of:
install Foreman as a pinned Python dependency in the isolated supervisor runtime if dependency compatibility is proven; or
use a second isolated environment such as `/opt/venv-foreman`.
Do not install Foreman into `/opt/venv-a0`.
Pin the exact source revision used.
---
6. Configuration and Secrets
Use environment variables / HF Space secrets only.
Suggested variables:
```text
# OpenTraining
OPENTRAINING_A2A_URL
OPENTRAINING_A2A_TOKEN
OPENTRAINING_A2A_PROJECT

# Supervisor identity
ARGUS_SUPERVISOR_CONTROLLER_ID=argus-openoperator
ARGUS_SUPERVISOR_ENABLED=1

# Heartbeat
ARGUS_SUPERVISOR_HEARTBEAT_SECONDS=120
ARGUS_SUPERVISOR_LEASE_TTL_SECONDS=600

# Argus runtime
ARGUS_SUPERVISOR_ARGUS_BIN=/opt/venv-argus/bin/argus
ARGUS_SUPERVISOR_ARGUS_HOME=/a0/usr/argus-supervisor/argus-home
ARGUS_SUPERVISOR_BACKEND=<configured supported backend>

# Foreman
ARGUS_SUPERVISOR_FOREMAN_ENABLED=1
ARGUS_SUPERVISOR_FOREMAN_BIN=<resolved isolated executable>
```
Rules:
never persist raw A2A tokens into logs;
never return token values through APIs;
report only boolean presence;
redact authorization headers;
do not place tokens in A2A task text;
do not expose a second public port;
use existing Space HTTPS ingress on `7860`.
---
7. OpenTraining A2A Client Contract
This adaptation is a client of OpenTraining.
Do not modify OpenTraining in this task.
Implement a narrow compatibility layer that expects the following logical operations:
```text
discover
submit
status
evidence
claim_control
renew_control
release_control
intervene
cancel
```
The adapter must isolate protocol details from the rest of the plugin.
Example interface:
```python
class OpenTrainingA2AClient:
    async def discover(self) -> AgentCapabilities: ...
    async def submit(self, request: SubmitRequest) -> RemoteTask: ...
    async def status(self, task_id: str) -> RemoteTaskStatus: ...
    async def evidence(self, task_id: str) -> EvidenceEnvelope: ...
    async def claim_control(self, campaign_id: str, controller_id: str) -> Lease: ...
    async def renew_control(self, campaign_id: str, lease: Lease) -> Lease: ...
    async def release_control(self, campaign_id: str, lease: Lease) -> None: ...
    async def intervene(self, task_id: str, request: InterventionRequest) -> RemoteTaskStatus: ...
    async def cancel(self, task_id: str, reason: str) -> RemoteTaskStatus: ...
```
If the currently deployed OpenTraining endpoint does not yet expose one of these operations, the adapter must:
feature-detect it;
expose the missing capability as unavailable;
fail closed for mutations;
continue read-only observation where possible.
Never simulate a successful remote mutation.
---
8. Long-Running A2A Behavior
Do not use one blocking request for a training campaign.
The existing Agent Zero blocking A2A helper has bounded waiting behavior and is not suitable as the sole lifecycle for multi-hour training.
Required model:
```text
submit
  ↓
receive durable remote task ID
  ↓
persist locally
  ↓
heartbeat polls compact state
  ↓
fetch evidence only when relevant
  ↓
Argus wakes only at a decision boundary
```
Persist:
```text
/a0/usr/argus-supervisor/
├── campaigns/
│   └── <campaign-id>.json
├── events/
│   └── <campaign-id>.jsonl
├── leases/
│   └── <campaign-id>.json
└── state/
    └── supervisor.json
```
Writes must be atomic where practical.
---
9. Campaign Model
Minimum local model:
```python
CampaignState(
    campaign_id: str,
    objective: str,
    remote_task_id: str | None,
    run_id: str | None,
    attempt_id: str | None,
    source_sha: str | None,

    remote_state: str,
    remote_stage: str | None,
    heartbeat_seq: int | None,

    controller_id: str | None,
    controller_epoch: int | None,
    lease_expires_at: datetime | None,

    latest_significant_event: dict | None,
    latest_evidence_ref: str | None,
    pending_question: dict | None,

    argus_project_id: str | None,
    argus_status: str,
    reviewer_verdict: str | None,

    created_at: datetime,
    updated_at: datetime,
)
```
---
10. Controller Lease
Even though only Face A is implemented now, implement lease-aware behavior so a future local LoopX controller can coexist safely.
Supervisor identity:
```text
argus-openoperator
```
Required properties:
controller identity;
monotonically changing controller epoch;
expiry;
renewal;
release;
stale-command rejection.
OpenOperator behavior:
```text
observer mode
    → may read status/evidence

controller mode
    → may submit/intervene/cancel only with valid lease
```
If lease renewal fails:
```text
stop mutation
remain observer
surface CONTROL_LOST significant event
```
Never retry a mutation using an expired controller epoch.
---
11. Heartbeat Design
11.1 Purpose
Heartbeat exists to:
detect remote state changes;
renew valid controller leases;
recover after transient transport failure;
wake Argus only for decision-worthy events.
It does not exist to create chat messages.
It must not be used to claim that Hugging Face Space sleep/availability can be bypassed.
11.2 Heartbeat loop
Conceptually:
```python
for campaign in active_campaigns:
    if campaign.owns_control:
        renew_lease_if_needed()

    remote = get_compact_status()

    if no_material_change(remote):
        persist_last_seen()
        continue

    event = reduce_remote_change(remote)
    persist_event(event)

    foreman_result = assess_if_needed(event)

    if should_wake_argus(event, foreman_result):
        notify_argus(event)
```
11.3 No-model fast path
Most heartbeat ticks must require zero LLM calls.
Do not wake Agent Zero, Argus, or Foreman when:
heartbeat sequence changed but state did not;
only elapsed time changed;
only routine training metrics changed within expected bounds;
remote log cursor advanced without a decision boundary.
---
12. Significant Event Reduction
Only these classes are user/supervisor significant by default:
```text
STATE_CHANGED
ATTEMPT_COMPLETED
BLOCKED
EVIDENCE_READY
CONTROL_CHANGED
MISSION_COMPLETED
REMOTE_UNAVAILABLE
```
Optional internal-only events may exist but must not enter normal chat output.
Examples:
suppress
```text
pip package downloaded
Git status inspected
training step 201/1000
heartbeat OK
still running
stdout chunk received
```
retain
```text
attempt failed
training entered RUNNING
checkpoint created
verification evidence ready
authentication required
controller lease lost
remote task disappeared
mission accepted
```
Deduplicate using stable event identity such as:
```text
campaign_id
remote_task_id
remote revision / heartbeat_seq
event type
evidence revision
```
---
13. Foreman Integration
Use `JsonLord/foreman-supervisor` as a bounded sentinel, not campaign owner.
Input should be reduced evidence, not raw entire transcripts.
Suggested projection:
```text
OpenTraining state/evidence
       ↓
FactoryObservation-compatible adapter
       ↓
Foreman responsibilities
       ↓
small directive
```
Useful checks:
```text
worker_health
implementation_complete
requirements_satisfied
tests_sufficient
needs_verification
human_escalation
```
Map Foreman directives into supervisor hints:
```text
CONTINUE         → no Argus wake unless another significant event exists
START_VERIFIER   → wake Argus Reviewer / verification stage
STEER_WORKER     → wake Argus Planner with evidence
STOP_WORKER      → request Argus decision; do not stop remotely by Foreman alone
RETRY_WORKER     → request Argus planning; do not retry remotely by Foreman alone
FINISH           → candidate completion only; Argus Reviewer must confirm
ESCALATE         → surface Needs you or Argus review
```
Foreman may not directly mutate OpenTraining.
This prevents competing supervisors.
---
14. Argus Bridge
Argus is a durable campaign supervisor.
Do not reimplement Argus's internal Manager/Planner/Engineer/Reviewer logic inside Agent Zero.
The plugin should adapt OpenOperator into an outer operator around Argus.
Responsibilities:
create/attach Argus mission;
provide bounded OpenTraining evidence;
deliver decision-worthy events;
query compact Argus status;
detect Argus `Needs you`;
persist mission binding;
relay authorized Argus decisions through the A2A client;
expose final Reviewer verdict.
Keep raw Argus traces local/persistent. Do not flood Agent Zero chat with them.
14.1 Argus mission contract
Initial Training Master mission should resemble:
```text
OBJECTIVE:
Make the named OpenTraining Training Master campaign satisfy its acceptance criteria.

AUTHORITY:
- read remote status/evidence
- inspect campaign evidence
- request repository repair through OpenTraining
- request bounded retries
- maximum attempts as configured
- no publication unless explicitly authorized
- no destructive Git actions
- no credential changes
- no force push
- no merge

EXECUTION:
All training execution must remain remote through OpenTraining.

ESCALATE:
- credentials/authentication
- spending/payment
- publication
- destructive actions
- controller conflict
- scope changes
- ambiguous high-impact choice

OUTPUT POLICY:
Do not narrate routine progress.
Return only blockers, attempt outcomes, stage transitions, reviewer verdicts, and mission completion.
```
---
15. Human-Facing Messaging Policy
Normal chat must not mirror internal events.
Only surface:
`NEEDS_YOU`
`ATTEMPT_COMPLETED`
`STAGE_TRANSITION`
`MISSION_COMPLETE`
critical control/infrastructure failure
Example acceptable message:
```text
Attempt 3 failed during Soup preprocessing.
Reviewer evidence: text-only dataset; engine attempted a messages-column removal.
Argus approved one bounded repair and started the next attempt.
```
Unacceptable:
```text
I checked git.
I loaded status.
The runtime is alive.
The test is still running.
The heartbeat succeeded.
I am now checking another file.
```
---
16. Agent Zero API Surfaces
Expose narrow authenticated endpoints through the existing Agent Zero HTTP service.
Suggested plugin APIs:
```text
GET  /api/plugins/argus-supervisor/health
GET  /api/plugins/argus-supervisor/status
GET  /api/plugins/argus-supervisor/campaigns
GET  /api/plugins/argus-supervisor/campaigns/{id}

POST /api/plugins/argus-supervisor/campaigns/{id}/observe
POST /api/plugins/argus-supervisor/campaigns/{id}/claim
POST /api/plugins/argus-supervisor/campaigns/{id}/release
POST /api/plugins/argus-supervisor/campaigns/{id}/pause
POST /api/plugins/argus-supervisor/campaigns/{id}/resume
POST /api/plugins/argus-supervisor/campaigns/{id}/cancel
```
Follow existing Agent Zero auth/CSRF conventions.
Do not create another listener or public port.
---
17. Startup and Recovery
On OpenOperator startup:
load persisted supervisor state;
verify Argus executable;
verify Foreman adapter if enabled;
feature-detect OpenTraining A2A;
reload active campaigns;
do not blindly reacquire control;
for locally recorded valid control:
check remote authoritative lease;
renew only if still owned;
resume heartbeat worker;
recover Argus mission bindings;
surface only material recovery failures.
After a Space restart, persisted local state is not enough to assume control.
Remote lease state is authoritative.
---
18. Failure Semantics
OpenTraining unavailable
```text
remote_state = unavailable
retain campaign
do not invent failure
backoff
retry read-only status
surface only after threshold or if user action needed
```
A2A timeout
Treat timeout as ambiguous.
Do not repeat a mutating operation unless idempotency/readback proves it safe.
Lost lease
```text
switch to observer
cancel pending local mutation intent
surface CONTROL_LOST
```
Argus unavailable
```text
OpenTraining execution may continue
heartbeat remains read-only
Foreman may continue bounded observation
no new mutations until Argus recovers or human takes control
```
Foreman unavailable
Argus may continue without Foreman.
Foreman is advisory/sentinel, not an availability dependency for remote execution.
---
19. Security Requirements
no new public port;
outbound HTTPS only for OpenTraining;
preserve existing Agent Zero token authority;
no token logging;
no secrets in Argus prompts;
no secrets in Foreman evidence;
no raw `.env` reads into model context;
sanitize remote errors;
cap evidence size;
ignore/sanitize remote HTML/markdown that attempts instruction injection;
treat remote evidence as data, not trusted instructions;
fail closed on mutation when controller authority is uncertain;
preserve immutable `/opt` runtime at runtime;
no `sudo` requirement in production startup.
---
20. Docker / Deployment Requirements
Adapt the existing Dockerfile on the Jules branch.
Build-time only:
install isolated Argus runtime;
install/pin Foreman adapter/runtime;
install any required non-runtime-mutating dependencies;
preserve non-root runtime behavior.
Runtime:
Agent Zero remains UID 1000;
no package mutation;
no root/sudo;
only port 7860;
persistent state only under `/a0/usr`.
Do not weaken existing HF deployment/SHA acceptance checks.
Extend live smoke testing to verify:
```text
Argus runtime present
Argus supervisor profile discoverable
plugin loaded
heartbeat health
OpenTraining A2A capability probe
secret masking
no second listener
```
---
21. Tests
Unit
Required tests:
```text
test_a2a_client.py
- auth header not logged
- feature detection
- timeout ambiguity
- malformed remote response
- read-only fallback
- mutation refusal without lease

test_campaign_store.py
- atomic save
- reload
- corruption handling
- event append
- restart recovery

test_event_reducer.py
- suppress noisy updates
- retain significant events
- deduplicate repeated revision
- attempt completion
- blocked
- control change

test_lease.py
- claim
- renew
- release
- expiry
- stale epoch rejection
- lost control → observer

test_heartbeat.py
- no LLM/model call on unchanged state
- wake on terminal attempt
- wake on blocker
- retry transient read
- no duplicate mutation

test_foreman_bridge.py
- reduced evidence only
- directive mapping
- Foreman cannot directly mutate remote

test_security.py
- token masking
- evidence truncation
- untrusted remote text treated as data
```
Integration
Use a fake A2A OpenTraining server.
Test:
```text
submit → running → completed
submit → running → failed
running → input-required
transport timeout + safe readback
lease lost during run
duplicate event delivery
Space/plugin restart during remote run
```
Live acceptance
Against actual OpenTraining:
discover endpoint;
attach read-only to a campaign;
claim a dedicated test campaign;
submit a harmless/small test task;
observe without status spam;
release control;
restart OpenOperator;
prove recovery from durable state;
confirm no duplicate remote attempt.
---
22. Acceptance Criteria
Implementation is complete only when all are true.
Runtime
[ ] `/opt/venv-a0` is untouched at runtime.
[ ] Argus has isolated runtime.
[ ] Foreman has isolated/pinned runtime or proven compatible isolated supervisor environment.
[ ] OpenOperator still runs non-root.
[ ] no additional public ports.
Agent Zero integration
[ ] `argus-supervisor` profile is discoverable.
[ ] plugin loads through normal plugin loader.
[ ] persistent supervisor state lives under `/a0/usr`.
[ ] APIs obey normal Agent Zero auth.
A2A
[ ] OpenTraining discovery works.
[ ] long-running tasks are non-blocking.
[ ] campaign/task IDs survive restart.
[ ] ambiguous mutations are not automatically replayed.
[ ] missing capabilities fail closed.
Control
[ ] observer vs controller mode is explicit.
[ ] lease identity and epoch are persisted.
[ ] stale authority cannot mutate remote state.
[ ] control loss switches to observer.
Noise control
[ ] routine heartbeat produces no user-visible message.
[ ] routine training stdout produces no chat output.
[ ] unchanged state causes no Argus model turn.
[ ] only significant event classes wake the supervisor.
Argus
[ ] Argus mission can be created/resumed.
[ ] `Needs you` can be surfaced.
[ ] final Reviewer verdict is visible.
[ ] routine Argus trace is not copied into chat.
Foreman
[ ] receives bounded evidence.
[ ] cannot directly execute OpenTraining mutations.
[ ] its output can trigger/skip Argus review.
[ ] outage does not stop an already-running remote task.
Recovery
[ ] OpenOperator restart does not duplicate a remote task.
[ ] stale local state does not silently reacquire control.
[ ] remote task can be reattached by durable ID.
---
23. Explicit Non-Goals
Do not implement in this task:
LoopX;
LoopX dashboard changes;
ACP integration;
local LoopX remote mode;
changes to OpenTraining source;
changes to Training Master;
direct Colab CLI integration in OpenOperator;
direct Kaggle integration in OpenOperator;
DGX routing;
generalized multi-service orchestration framework;
new public service ports;
replacement of Agent Zero's A2A server;
replacement of Agent Zero scheduler;
replacement of Argus internal Manager/Planner/Engineer/Reviewer architecture;
Foreman as a second campaign owner.
---
24. Recommended Delivery Order
Phase 1 — skeleton
Argus profile
plugin
models/store
health
config
isolated runtime wiring
Phase 2 — read-only A2A
discovery
remote status
remote evidence
persistence
event reducer
heartbeat
No remote mutation yet.
Phase 3 — Argus observation
Argus mission binding
significant event wakeups
compact status
Needs-you surfacing
Phase 4 — Foreman gate
evidence projection
bounded assessment
Argus wake/no-wake decision
Phase 5 — controller mode
claim/renew/release
controller epoch
guarded mutate/cancel/intervene
fail-closed behavior
Phase 6 — restart and live qualification
live OpenTraining test
Space restart
duplicate-event test
lease-loss test
no-status-spam validation
---
25. Final Required Report
At completion report:
```text
branch
base SHA
final SHA

files added/changed

Argus:
  version/source pin
  executable
  persistent state root
  backend configuration source

Foreman:
  version/source pin
  integration mode

OpenTraining:
  endpoint capability results
  auth mode
  read-only operations proven
  mutating operations proven

Heartbeat:
  cadence
  no-model fast-path proof
  significant event classes

Control:
  controller id
  lease behavior
  stale epoch test

Tests:
  unit
  integration
  live acceptance

Deployment:
  HF Space build result
  deployed SHA
  /health SHA match

Known limitations
```
Do not merge into `main` unless separately instructed.
