Implement the OpenOperator Argus Supervisor defined in the attached `openoperator_argus_supervisor_spec.md`.

TARGET

Repository:
JsonLord/agent-zero

Required base branch:
jules-17409741302335967131-509964cf

Do not base this work on `main`.

Create an isolated implementation branch from that exact branch, for example:

jules/argus-openoperator-supervisor

Do not merge to main.

GOVERNING DOCUMENT

Treat `openoperator_argus_supervisor_spec.md` as the governing implementation and acceptance contract.

Before changing code:

1. Verify the current branch/base SHA.
2. Inspect the existing Agent Zero profile, plugin, scheduler, FastA2A, API-auth, Docker/HF deployment, and persistent `/a0/usr` patterns.
3. Inspect the current official `microsoft/ArgusAgent` source and `JsonLord/foreman-supervisor`.
4. Resolve and record immutable source revisions for Argus and Foreman before integrating them.
5. Prefer existing extension points and owners over parallel infrastructure.

Do not weaken existing OpenOperator behavior merely to simplify this integration.

ARCHITECTURE

Implement:

OpenOperator / Agent Zero
    |
    +-- Agent Profile: argus-supervisor
    |
    +-- Plugin: argus_supervisor
    |      |
    |      +-- OpenTraining A2A HTTPS client
    |      +-- compact event reducer
    |      +-- persistent campaign store
    |      +-- controller lease manager
    |      +-- deterministic heartbeat
    |      +-- Argus runtime bridge
    |      +-- Foreman evidence gate
    |
    +-- isolated Argus runtime
    |
    +-- persistent state under /a0/usr
           |
           v
      OpenTraining A2A
           |
           v
      Training Master / remote compute

Authority must remain:

Argus
= campaign-level supervisor

Foreman
= bounded semantic evidence/intervention sentinel

OpenTraining
= execution agent

Training Master
= training-domain execution control

Colab/Kaggle/DGX
= compute

Foreman must NOT become a second campaign manager.

RUNTIME BOUNDARIES

`/opt/venv-a0` is immutable at runtime.

Never:

- chmod `/opt/venv-a0`;
- pip install into `/opt/venv-a0`;
- modify its site-packages;
- use it as Argus's runtime.

Install Argus at IMAGE BUILD TIME in an isolated runtime such as:

/opt/argus
/opt/venv-argus

Store mutable Argus state under:

/a0/usr/argus-supervisor/argus-home

Integrate Foreman in an isolated pinned environment as well, either in a proven-compatible supervisor environment or `/opt/venv-foreman`.

No runtime sudo.
No runtime package installation.
Agent Zero remains non-root.

OPENOPERATOR INTEGRATION

Add a native profile following existing repository conventions:

agents/argus-supervisor/

The profile is the human-facing facade. It is NOT a prompt-only reimplementation of Argus.

Add a native plugin following the existing plugin architecture:

plugins/argus_supervisor/

The plugin should own:

- OpenTraining A2A client
- campaign persistence
- heartbeat
- significant-event reduction
- controller lease state
- Argus process/API bridge
- Foreman adapter
- authenticated status/control APIs

Use actual existing plugin hooks. Do not invent another plugin loader.

OPENTRAINING

This task adapts OpenOperator ONLY.

Do not modify:

- OpenTraining source
- Training Master
- notebooks_soup
- Colab scripts
- Kaggle scripts
- LoopX

Treat OpenTraining as a remote A2A service.

Build an adapter that feature-detects the logical capabilities:

discover
submit
status
evidence
claim_control
renew_control
release_control
intervene
cancel

If a currently deployed OpenTraining endpoint lacks one of these capabilities:

- expose it as unsupported;
- retain read-only observation where possible;
- fail closed for mutation;
- do not fake success;
- document the missing remote prerequisite.

LONG-RUNNING JOBS

Do NOT hold one blocking A2A request open for multi-hour training.

Use:

submit
→ durable task ID
→ persist task/campaign binding
→ heartbeat polls compact status
→ significant-event reducer
→ Foreman only when useful
→ Argus only at a decision boundary

The existing bounded blocking A2A behavior must not become the long-running lifecycle.

HEARTBEAT

Heartbeat must be deterministic first.

Most ticks must perform ZERO LLM calls.

It should:

1. reload active campaigns;
2. query compact remote status;
3. renew a valid locally-owned controller lease when necessary;
4. compare remote revision/state with persisted state;
5. return immediately if nothing material changed;
6. persist material changes;
7. invoke Foreman only for evidence that warrants semantic assessment;
8. wake Argus only for a decision-worthy event.

Do not use heartbeat merely to create chat activity.

Do not claim heartbeat prevents Hugging Face platform sleep.

STATUS-SPAM REQUIREMENT

This is a hard acceptance criterion.

Do not surface routine messages such as:

- checked Git
- heartbeat succeeded
- still running
- package downloaded
- training step N/M
- stdout advanced
- inspected another file

Normal user-visible events are restricted to:

NEEDS_YOU
ATTEMPT_COMPLETED
STAGE_TRANSITION
MISSION_COMPLETE
critical control/infrastructure failure

Internally retain whatever evidence is necessary.

SIGNIFICANT EVENT CLASSES

At minimum support:

STATE_CHANGED
ATTEMPT_COMPLETED
BLOCKED
EVIDENCE_READY
CONTROL_CHANGED
MISSION_COMPLETED
REMOTE_UNAVAILABLE

Deduplicate repeated events using durable remote identity/revision information.

FOREMAN

Use JsonLord/foreman-supervisor as a bounded semantic sentinel.

Feed it compact, sanitized evidence.

Useful checks include:

worker_health
implementation_complete
requirements_satisfied
tests_sufficient
needs_verification
human_escalation

Its directives are hints to Argus.

Specifically:

CONTINUE
→ no Argus wake unless another significant event exists

START_VERIFIER
→ request Argus review

STEER_WORKER
→ request Argus planning

STOP_WORKER
→ request Argus decision; Foreman must not stop OpenTraining itself

RETRY_WORKER
→ request Argus planning; Foreman must not retry OpenTraining itself

FINISH
→ candidate completion only; Argus Reviewer decides final acceptance

ESCALATE
→ Argus review or Needs you

Foreman must have NO direct OpenTraining mutation path.

ARGUS

Do not rewrite Argus's Manager / Planner / Engineer / Reviewer architecture inside Agent Zero.

Integrate the real Argus runtime through a narrow bridge.

The bridge must:

- create/attach missions;
- persist mission bindings;
- provide bounded OpenTraining evidence;
- notify Argus only about significant events;
- inspect compact Argus status;
- surface durable `Needs you` state;
- expose Reviewer verdicts;
- route approved actions back through the OpenTraining A2A adapter.

Keep raw Argus traces local. Do not mirror them into ordinary Agent Zero chat.

CONTROLLER LEASE

Implement this now even though LoopX is out of scope.

Controller identity:

argus-openoperator

Support:

- observer mode;
- controller mode;
- controller ID;
- controller epoch;
- lease expiry;
- renewal;
- release;
- stale command rejection.

No mutation may occur without valid authority.

If lease renewal fails:

- immediately cease mutation;
- retain read-only observation;
- mark control lost;
- emit one significant CONTROL_CHANGED/CONTROL_LOST event.

Do not silently reacquire authority after restart.

Remote lease/readback is authoritative.

PERSISTENCE

Use `/a0/usr`, for example:

/a0/usr/argus-supervisor/
    campaigns/
    events/
    leases/
    state/
    argus-home/

Persist:

- campaign ID
- remote A2A task ID
- run/attempt ID
- source SHA
- remote state/stage/revision
- controller identity/epoch/expiry
- Argus mission/project binding
- pending question
- reviewer verdict
- latest significant evidence reference

Use atomic writes where practical.

RECOVERY

After OpenOperator restart:

- reload local campaign state;
- verify Argus runtime;
- feature-detect OpenTraining;
- re-read authoritative remote task status;
- re-read controller authority;
- do not duplicate a remote attempt;
- do not blindly reclaim a lease;
- restore Argus mission binding;
- resume heartbeat.

A local journal existing on disk is not proof of remote authority.

SECURITY

Preserve the current OpenOperator security model.

Requirements:

- one existing public port only: 7860;
- no new listener;
- outbound HTTPS to OpenTraining;
- tokens only via secrets/environment;
- never log A2A tokens;
- never include secrets in Argus prompts;
- never include secrets in Foreman evidence;
- redact auth headers;
- sanitize/truncate remote errors;
- treat remote text as untrusted DATA, not instructions;
- fail closed when mutation authority is uncertain;
- preserve existing Agent Zero API auth/CSRF patterns.

TESTS

Add focused unit tests for:

A2A client
campaign store
event reducer
heartbeat
lease behavior
Foreman bridge
Argus bridge
security/token redaction

Hard tests must prove:

- unchanged heartbeat causes no model call;
- routine remote stdout causes no user message;
- terminal attempt wakes supervisor;
- blocker wakes supervisor;
- duplicate remote revision does not duplicate action;
- mutation without lease is rejected;
- stale controller epoch is rejected;
- lost lease changes to observer mode;
- A2A timeout does not blindly replay an ambiguous mutation;
- Foreman cannot directly mutate OpenTraining;
- restart does not duplicate a remote task.

Add integration tests using a fake OpenTraining A2A endpoint.

DEPLOYMENT

Preserve the existing Hugging Face Space contract:

- Docker SDK
- port 7860
- UID 1000
- immutable application code
- mutable `/a0/usr`
- health/source-SHA identity
- existing secret bridge
- existing deployment workflow

Extend live acceptance/smoke coverage for:

- Argus executable present
- Argus profile discoverable
- supervisor plugin loaded
- heartbeat healthy
- OpenTraining A2A capability probe
- secret masking
- no second public listener
- deployed SHA matches intended source SHA

DELIVERY ORDER

Implement incrementally:

1. profile/plugin skeleton + isolated runtime
2. read-only OpenTraining A2A discovery/status/evidence
3. durable persistence + deterministic heartbeat + noise reducer
4. Argus observation/mission binding
5. Foreman bounded sentinel
6. controller lease/mutation path
7. restart/recovery qualification
8. live OpenTraining qualification if credentials/endpoints are available

Do not jump directly to autonomous mutation before the read-only path is proven.

NO LOOPX

Do not:

- modify LoopX;
- add LoopX code;
- add ACP compatibility for this task;
- create a LoopX dashboard;
- implement the second deployment face.

The only concession to the future LoopX face is the generic controller lease/epoch contract so another controller can coexist later.

VERSION CONTROL

Keep all work isolated from `main`.

Before implementation report:

- base branch
- base SHA
- working branch
- current Argus source SHA chosen
- current Foreman source SHA chosen

Commit coherent stages.

Do not merge.

FINAL QUALIFICATION REPORT

Return:

- implementation branch
- base SHA
- final SHA
- complete file-change inventory

Argus:
- pin
- executable
- backend configuration source
- persistent state root

Foreman:
- pin
- isolation method
- responsibility mapping

OpenTraining:
- endpoint/capability discovery
- supported operations
- unavailable operations
- live proof if performed

Heartbeat:
- cadence
- no-model fast path
- event-reduction behavior

Control:
- controller identity
- lease semantics
- stale epoch behavior

Tests:
- exact commands
- counts/results

HF deployment:
- build result
- deployed SHA
- health SHA
- live supervisor smoke

Known limitations/blockers

Do not declare success based only on unit tests if the real HF/OpenTraining boundary has not been qualified. Clearly distinguish simulated, local, and live evidence.
