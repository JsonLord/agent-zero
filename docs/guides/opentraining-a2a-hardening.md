# OpenTraining A2A deployment and local qualification

This work starts from `opentraining@1b64876b409337b2d11e6fe789809d99eb1fddb8`.
It changes only the OpenTraining branch. No OpenOperator/Argus implementation or
controller mutation protocol is included.

## Verified source assumptions

- Requirements pin FastA2A 0.5.0, Starlette 1.0.1 and Pydantic 2.11.7.
- Generic settings default A2A to false; `create_auth_token()` generates the existing
  `mcp_server_token` from persistent runtime identity and configured login credentials.
  The bootstrap never creates a second credential authority or stores this token.
- README declares `sdk: docker`. Docker CMD runs `/a0/start_openoperator.sh`, which
  prepares Training Master and hands off to `docker/hf/initialize_hf.sh`. Supervisor
  then runs `/opt/venv-a0/bin/python /a0/run_ui.py` on the existing port 7860.
  This is evidence for the intended checked-in HF startup, not proof of the live
  Space's installed revision. No production request was made in this task.
- Both dedicated HF launchers now call `scripts/configure_hf_a2a.py` before application
  initialization. It atomically enables A2A in `<application-root>/usr/settings.json`,
  preserves unrelated fields, removes any persisted generated-token field, and fails
  without overwriting malformed JSON. New settings files have mode 0600.
- The optional `start_hf.sh` was an implicit default-branch clone plus non-overwriting
  copy and patch overlay. It now fetches an explicit `OPENTRAINING_SOURCE_REF`
  (default `opentraining`; **set the reviewed exact SHA for reproducible deployment**),
  executes a clean detached checkout, and links existing usr/logs/tmp/per directories.
  It does not delete the original app or its Training Master experiments/configuration.
  Persistent identity and credentials remain under the linked `usr/.env`.
- The new source launcher no longer applies patches. The existing UI overlay is retained
  for compatibility; both it and the canonical UI import the same discovery route
  factory and the same A2A proxy. Existing unrelated overlay behavior is not expanded.
- The legacy `/api-docs` overlay referenced `api.api_docs`, which does not exist in this
  branch. The shared public endpoint now serves safe integration-contract metadata.
- Streaming was incorrectly advertised. FastA2A 0.5's stream method is unimplemented;
  cards and machine docs now correctly advertise streaming false.

## Identity and discovery

`A0_PUBLIC_URL` is an optional explicit HTTP(S) origin. Otherwise use documented HF
`SPACE_HOST` or `SPACE_ID`, with the dedicated OpenTraining URL as the legacy HF fallback.
The incorrect baked-in OpenOperator URL is removed. Credentials, query strings,
fragments, non-root paths and HF localhost identity are rejected.

Public endpoints `/health`, `/docs`, `/docs/a2a.json` and `/api-docs` contain no
credentials or model/provider data. `/health` reports a source SHA only when an actual
`opentraining-build.json` manifest exists; the source launcher writes its fetched SHA.
The current Docker path has no source manifest producer: the later exact-SHA delivery
must supply the reviewed manifest if health provenance is required. No SHA is fabricated.

Both authenticated card paths resolve through the real router and return equivalent
JSON: `/a2a/.well-known/agent.json` and `/a2a/.well-known/agent-card.json`.
`/a2a/docs` remains FastA2A's authenticated library documentation.

All RPC uses **POST /a2a/**. `message/send`, `tasks/get` and `tasks/cancel` are method
names, not URL paths. Use `messageId`, `contextId`, `acceptedOutputModes` and
`historyLength` on the wire. Authentication uses generated-token Bearer or X-API-KEY
headers. Legacy token/project paths remain compatible; query-string credentials are
not accepted. Empty token authority returns 503 before any worker startup; absent or
wrong credentials return 401. Invalid schema returns bounded JSON-RPC -32600 / HTTP400.
No browser/session auth or CSRF behavior is weakened.

## Local checks

Use the framework virtualenv, not the agent execution environment:

```sh
python -m pytest -q tests/test_fasta2a_server.py tests/test_fasta2a_client.py tests/test_opentraining_a2a.py
python -m pytest -q tests/test_http_auth_csrf.py tests/test_webui_startup_assets.py
python -m compileall -q helpers scripts
bash -n start_hf.sh start_openoperator.sh docker/hf/initialize_hf.sh scripts/qualify_opentraining_a2a.sh
git diff --check
```

Real ASGI tests use pinned Starlette/FastA2A schemas, task manager, in-memory broker,
storage and AgentZeroWorker, with Agent Zero/model execution replaced by deterministic
local behavior. They cover submitted→completed task readback, response identity/text,
auth, card serialization, malformed wire, bootstrap and discovery. A bounded stress
check concurrently completes 64 distinct task lifecycles and rejects 64 unauthorized
submissions without starting extra agents. It asserts clean worker/context cleanup.
An executed launcher fixture fetches an exact SHA from a local Git repository, runs the
bootstrap from the detached source, and proves persistent training state survives.
The existing auth test fixture needed its missing production `serve_index` route;
its protected-behavior assertions remain unchanged.

These checks validate the local protocol/control plane, **not** live provider capacity,
network/proxy behavior, durable task recovery or cross-Space controller mutations.
FastA2A uses volatile storage; task identity is lost on restart. Cancellation remains
best effort and is not a guarantee that model-side effects stop. The generic assistance
capability must not be interpreted as a qualified training/controller mutation API.

`scripts/qualify_opentraining_a2a.sh` is for Jules/operator use **after review and exact-SHA
deployment**, with OPENTRAINING_A2A_TOKEN securely configured. That variable is a client
credential only; OpenTraining's inbound authority remains the generated settings token.
The script rejects redirects, does not print credentials or raw authenticated responses,
and polls a harmless task to completion. It was syntax-checked only; this task does not
deploy, mutate Space secrets, run production traffic or execute cross-Space tests.

## Validation results

The focused A2A suite passes 23 tests; the expanded A2A/auth/CSRF/settings/WebUI suite
passes 46 tests with no skips. Compileall, four shell syntax checks, new-module Ruff
and whitespace validation pass. The executed bounded stress case is included in that
count; the qualification script has not been run against any remote service.

An additional Docker initializer suite exposed two **pre-existing** failures:
`test_initialize_raises_soft_open_file_limit_to_requested_target` and
`test_initialize_caps_open_file_limit_at_hard_limit`. Both expect a
`raise_open_file_limit()` function absent from `docker/run/fs/exe/initialize.sh` in the
base commit. The test and initializer are unchanged relative to the specified base.
They concern a different launcher from the dedicated HF path; no unrelated runtime
change is included. Expanded run including those tests: 46 passed, 2 failed.

Security scans of tracked/new source and the complete patch found zero occurrences
of the known exposed credential and zero high-confidence provider-token/private-key
literals. This is a scoped pattern scan, not a proof against every possible secret.
No deployment or production traffic was performed. The feature branch can be reviewed
and CI-tested by Jules; the unrelated baseline failures and absent Docker manifest
producer remain explicit handoff limitations before production qualification.
