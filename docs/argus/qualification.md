# Argus Face A qualification

Status: implemented for review and locally qualified; **not HF/OpenTraining live
qualified**. Unit/integration success is not a production acceptance claim.

## Source and delivery identity

- Required base: `jules-17409741302335967131-509964cf`.
- Base SHA: `8f30a6549b87fd103d50b26170bb5ab57b032209`.
- Implementation branch: `jules/argus-openoperator-supervisor`; never based on main.
- Final delivery SHA: recorded by the review PR and final delivery message;
  `git rev-parse HEAD` identifies this checkout exactly.
- Complete inventory: [files-changed.txt](files-changed.txt), relative to the base.
- Governing [specification](openoperator_argus_supervisor_spec.md) and
  [implementation prompt](implementation-contract.md) are preserved with normalized
  line endings/trailing whitespace. No substantive requirements were removed.

## Argus and Foreman

| Boundary | Source pin | Qualification |
| --- | --- | --- |
| Microsoft ArgusAgent, Argus 0.1.8 | `fdfeb715b0749db176c7d8b3212a717fb81087ba` | Git revision resolved and inspected; package installed in separate local venv; pure CLI `python -m argus --version`; actual MemoryBundle project create/reopen/observe, no model call |
| JsonLord foreman-supervisor, foreman-core 0.5.0 | `381ca2de90af9efc2781a58055cc3028c7cabbb9` | Git revision resolved and inspected; separate local venv; actual FactoryObservation, builtin responsibility checks, JevForemanModel and FactoryPolicy exercised with a controlled SDK response |

Image destinations are `/opt/argus`, `/opt/venv-argus`, `/opt/foreman` and
`/opt/venv-foreman`; all installed at build time using source SHA verification and
qualified dependency constraints. This change never installs into or chmods the
framework venv. Both local isolated environments pass `pip check`.

Argus's installed executable is `/opt/venv-argus/bin/argus`. The bridge uses
`/opt/venv-argus/bin/python` and pinned upstream APIs instead of the executable's
TUI/web-launch path. A significant event invokes the real Manager/LifeSupervisor
role pipeline, finite once-only mission budget, two-round cap and 120-second
process timeout. Argus's own Manager/Planner/Engineer/Reviewer roles are retained.
The selected upstream backend must be separately configured through
`ARGUS_SUPERVISOR_BACKEND`, upstream `ARGUS_SKILL_*` model settings, provider CLI
and provider credentials. No default backend or main-chat configuration is invented.
The configured upstream daily USD cap is passed through. No live model turn was run.

Mutable Argus state is `/a0/usr/argus-supervisor/argus-home`; Foreman state is
`/a0/usr/argus-supervisor/foreman-home`. Campaigns, event outbox, lease diagnostics,
mutation intents and heartbeat receipt live in sibling campaigns/events/leases/state
folders. Argus project IDs and remote task IDs survive reopen. No remote submission
or takeover is performed by recovery.

Foreman checks completion, requirements, verification, worker health and human
escalation. Inputs are bounded data, not raw transcripts. CONTINUE can suppress a
pure evidence wake; other directives only request Argus review/planning. FINISH is
candidate completion. STOP/RETRY never directly execute remotely. Upstream's
additional START_WORKER directive maps to a STEER_WORKER planning hint. Foreman
outage is advisory. It receives no OpenTraining client or credential environment.

## OpenTraining live boundary

Target origin: `https://leon4gr45-opentraining.hf.space`; application A2A base is
`/a2a`. Configure the token separately as `OPENTRAINING_A2A_TOKEN`, never in a
persisted URL, task, prompt or report.

Read-only live probes tried the supplied tokenized endpoint with authentication
headers and the requested alternate token. Agent-card variants and the A2A base
were attempted. Every connection failed at the cloud proxy CONNECT stage with
`403 Forbidden`, before a remote HTTP/authentication response. An independent
origin `/health` probe confirmed the same denial. No credentials were printed,
no training task was submitted, and no remote control was claimed.

Therefore **all deployed remote capabilities and authentication are unknown**.
The provided token was not shown to be valid or invalid; the alternate token was
not shown to work. There is no live evidence of lease support, durable remote
request IDs, a dedicated test campaign, submission, evidence, cancellation or
remote restart recovery. Nothing was changed in OpenTraining/Training Master.

The [compatibility contract](a2a-compatibility.md) documents standard A2A reads and
the explicit campaign-control extension. Standard methods are tentative until
called. Remote lease/epoch **and execution-policy enforcement** must be advertised
before control methods are enabled. Readback must prove authority for each write.
The adapter also requires request-ID readback to reconcile ambiguous writes.
Missing operations remain unsupported; generic A2A skill descriptions cannot grant
permission. This is an explicit remote prerequisite, not a claim that the deployed
service already implements it.

The cloud configuration draft adds only the missing OpenTraining domain while
preserving the allowlist, an optional secure token requirement, a non-secret A2A
base suggestion, and reproducible isolated local setup. Saving does not apply or
publish it, populate a secret, or change HF secrets. Review/save and publish that
cloud configuration to remove the current network prerequisite; retry discovery
before attempting any mutation.

## Heartbeat, authority and messages

Default heartbeat is 120 seconds, serviced by the existing 60-second job loop
(rounding configured cadence upward to a job-loop boundary). Startup migration is
synchronous and schedules retained recovery through the existing DeferredTask
owner. Model work cannot block the scheduler. The single bounded tick has a global
file lock; campaign locks serialize APIs and heartbeat across threads/processes.
No replacement scheduler or auxiliary listener exists.

The no-model path ignores heartbeat sequence, elapsed time, routine metrics and
stdout/cursor advancement. Material event classes are STATE_CHANGED,
ATTEMPT_COMPLETED, BLOCKED, EVIDENCE_READY, CONTROL_CHANGED, MISSION_COMPLETED and
REMOTE_UNAVAILABLE. Event identity and delivery receipt persist atomically with
the campaign. API-visible events are restricted to Needs you, attempt outcomes,
stage transitions, mission completion and critical control/infrastructure failure.
The heartbeat does not write chat messages or prevent HF sleep.

Controller identity defaults to `argus-openoperator`. Authority requires controller
mode, matching integer epoch, unexpired local lease and fresh authoritative remote
readback. Renewal is due below half the configured TTL (default 600 seconds).
Failure immediately changes to observer and records one durable control-loss event.
Recovery never claims authority from a journal or silently reacquires it.

Writes save a unique request intent before network I/O; timeout/cancellation leaves
an unknown intent and blocks retries. Reconciliation requires remote request-ID
readback and never resends. Submissions are nonblocking and bounded by configured
attempt count (default 3, max 20). Active tasks cannot be blindly replaced.
Argus proposals additionally need a fresh independent Reviewer verdict for that
exact event; consumed decision IDs prevent duplicate relay. Campaign completion
requires that verdict, an explicit completion proposal and completed remote state.
Every remote write carries an immutable remote-only/no-publication/no-destructive-
Git/no-credential-change/no-force-push/no-merge policy for remote enforcement.

## Executed checks

Local supervisor selection: **66 passed**, including two actual isolated upstream
package contract tests; zero failed/skipped when the two runtime variables are set.
The full selected regression command below: **507 passed**, zero failed/skipped.
It retains the base's Spynel routing/dispatch, naming, search/Tinyfish/SearXNG startup,
A2A, HF controls, settings, auth/CSRF, profiles, Colab and repository contracts.

```bash
export ARGUS_TEST_ARGUS_PYTHON=/workspace/venvs/argus/bin/python
export ARGUS_TEST_FOREMAN_PYTHON=/workspace/venvs/foreman/bin/python
/workspace/venvs/openoperator/bin/python -m pytest \
  plugins/argus_supervisor/tests plugins/_chat_naming/tests plugins/_goal/tests \
  tests/test_spynel.py tests/test_spynel_resolver.py \
  tests/test_spynel_dispatch_integration.py tests/test_spynel_profile_guard.py \
  tests/test_search_reliability.py tests/test_tinyfish_fallback.py \
  tests/test_document_query_plugin.py tests/test_document_query_fallback.py \
  tests/test_hf_deployment_control.py tests/test_hf_searxng_startup.py \
  tests/test_specialist_profiles.py tests/test_subagent_profiles.py \
  tests/test_hf_space_defaults.py tests/test_prompt_improver.py tests/test_colab_a0.py \
  tests/test_blocking_a2a.py tests/test_fasta2a_server.py tests/test_fasta2a_client.py \
  tests/test_goal_state_contract.py tests/test_http_auth_csrf.py \
  tests/test_api_token_authority.py tests/test_sidebar_row_actions.py \
  tests/test_settings_probe.py tests/test_runtime_dockerized.py \
  tests/test_settings_root_password.py tests/test_settings_mcp.py tests/test_hf_smoke.py \
  tests/test_memory_extension_hf.py tests/test_webui_icons.py \
  tests/test_tiny_coder_model_binding.py tests/test_worktree_isolation_contract.py -q
/workspace/venvs/openoperator/bin/ruff check plugins/argus_supervisor
/workspace/venvs/openoperator/bin/python -m compileall -q plugins/argus_supervisor
bash -n docker/run/fs/ins/install_argus_supervisor.sh
git diff --check 8f30a6549b87fd103d50b26170bb5ab57b032209
/workspace/venvs/argus/bin/python -m argus --version
/workspace/venvs/argus/bin/python -m pip check
/workspace/venvs/foreman/bin/python -m pip check
```

Fake OpenTraining integration uses real loopback HTTP through the real aiohttp
adapter: submit → working → completed/failed/input-required; durable reopen;
duplicate revision; no resubmit; takeover/lost lease. Unit checks cover ambiguous
write timeout/readback, missing capabilities, malformed responses, expiry/stale
epoch, failed renewal, interrupted model turns, atomic-write failure, corruption,
no routine chat output, Foreman isolation and environment/token masking. The
normal plugin loader finds the profile/hooks; the normal API dispatcher enforces
login and CSRF. CI now installs both isolated pinned packages for contract checks.
No tests were replaced with stub acceptance or disabled to obtain these results.

## HF release acceptance still required

Build result: **not run**. Deployed SHA: **not established**. Live `/health` SHA
match: **not established**. Live supervisor smoke: **not run**. No local Docker
build, HF upload/restart, deployment workflow trigger, main/production push or merge
was performed. Existing UID 1000, port 7860, health/source-SHA publishing and
persistent `/a0/usr` contracts remain intact.

After separately authorized build/release, run inside the exact container:

```bash
cd /a0
ARGUS_EXPECTED_SOURCE_SHA=<approved-full-sha> \
  /opt/venv-a0/bin/python -m plugins.argus_supervisor.runtime.smoke
```

The read-only command checks both real runtimes, loader/profile, persistent
heartbeat receipt, capability discovery, UID, build SHA, live `/health` SHA and
non-loopback TCP listeners. It returns failure for missing acceptance evidence;
it never claims/submits or prints credentials. Inspect authenticated plugin health
and status for only boolean secret presence and significant events. The serving
process must be enabled/configured for heartbeat checks; an in-process singleton
created by the smoke command is not treated as proof of a running heartbeat.

Then qualify live read-only attachment first. Only if lease/policy/readback
capabilities are proven, explicitly claim a dedicated disposable test campaign,
submit a harmless task, observe to completion, release, and perform an authorized
restart. Verify persisted task/mission IDs, authoritative epoch, no duplicate
remote attempt and no status spam. Do not remove journal files to force a retry.

## Known limits

No real Argus backend credentials or Foreman provider credentials were configured;
actual model decisions and Reviewer acceptance are unverified. Installed Argus
observation and Foreman assessment/policy plumbing were tested as described above.
Argus subprocesses/dependencies are isolated; a separately configured trusted CLI
backend is not an OS sandbox. The host's existing security model still governs
that backend. Native API routes use repository POST conventions rather than
introducing REST listeners/routes. No custom dashboard is added. Runtime and live
memory/cost measurements remain unqualified. All live acceptance criteria remain
open until the remote/HF boundary is actually exercised.
