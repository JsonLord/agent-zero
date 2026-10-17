# Deterministic HF external integrations

Starting source SHA: `8ca0c0d20ebf045fb2e62905176546a11e507dcb`.
Branch: `jules/argus-openoperator-supervisor`; review remains PR #29, no merge.
Final committed delivery SHA is recorded in the PR and delivery message.

## Runtime and token authority

`helpers.runtime.is_huggingface_space()` detects nonblank `SPACE_ID`, the documented
Space variable. `HF_SPACE` does not control detection. This is not authentication;
`requires_auth` and `csrf_protect` have no HF bypass. Browser settings/message
endpoints retain normal session/login and CSRF behavior. External
`/api/settings_probe` and `/api/api_message` retain API-key auth without browser
cookies or CSRF.

Set the operator-owned HF **secret** `SPYNEL_AGENT_ZERO_API_KEY` before releasing.
Use a random value chosen/stored by the operator. It is the shared incoming
API/MCP/A2A credential; this change never invents or reveals a production key.
On a Space, no canonical key means missing authority even if old settings or
`A0_SET_MCP_SERVER_TOKEN` exist. MCP/A2A are disabled and external key endpoints
return 503 with a safe missing-token diagnostic. The UI can still boot.

Locally the order remains deployment secret → persisted environment
`A0_SET_MCP_SERVER_TOKEN` → configured token → stable generated local token.
Source diagnostics use only `deployment_secret`, `persisted_environment`,
`configured`, `generated_local`, `missing`. Generated local authority never counts
as production-ready on a Space.

The HF entrypoint explicitly sets both MCP and A2A enabled flags according to
canonical-secret presence and prints only a safe enabled/disabled message. Settings
normalization enforces the same rule, protecting against stale persistent flags.
The real key remains masked as `************` in settings output. Safe metadata is
available through authenticated browser settings `additional.external_services`
and API-key-protected settings_probe `external_services`: presence, source,
effective enabled flags and a missing-token diagnostic. Neither tokens nor hashes
are returned; `/health` remains source provenance only.

## Connections

Replace `YOUR_SPYNEL_AGENT_ZERO_API_KEY` in the examples with the value you stored
as the HF secret. The token is intentionally not retrievable from OpenOperator.
The UI never substitutes the settings mask into an executable connection example.

- External API: POST `/api/settings_probe` or `/api/api_message`, header
  `X-API-KEY: YOUR_SPYNEL_AGENT_ZERO_API_KEY`.
- A2A: `/a2a` with `Authorization: Bearer YOUR_SPYNEL_AGENT_ZERO_API_KEY` or
  `X-API-KEY`, or compatible `/a2a/t-YOUR_SPYNEL_AGENT_ZERO_API_KEY` path.
- MCP SSE: `/mcp/t-YOUR_SPYNEL_AGENT_ZERO_API_KEY/sse`.
- MCP streamable HTTP: `/mcp/t-YOUR_SPYNEL_AGENT_ZERO_API_KEY/http`.

Existing MCP uses token-path routing, not newly invented header auth. A2A retains
both header modes and token-path compatibility. All use the existing port 7860.
Never post the real URLs/headers/tokens in chat, logs or Argus evidence.

## Exact-SHA deployment

`scripts/deploy_hf_space.py` checks tracked and untracked worktree changes before
any upload and refuses dirty state. There is no implicit dirty-tree override.
It resolves the requested commit to its full SHA, prints local HEAD, deployment
SHA, clean state and HF target, then archives only that commit. A historical
`--sha` is explicitly identified. `openoperator-build.json` records that exact
resolved SHA. The HF credential stays in the subprocess environment/askpass
channel, not a credential-bearing Git remote URL or printed transport output.

After a clean commit and authorized branch push:

```bash
python scripts/deploy_hf_space.py \
  --sha <approved-full-source-sha> --space Leon4gr45/openoperator --verify
```

The operator must configure the canonical secret in the **HF Space** first.
Authenticated upload also needs `HF_TOKEN` with write access to that Space.
Provide credentials through secure environment bindings, never command arguments
or chat. Successful push alone is not qualification. `--verify` requires live
`https://leon4gr45-openoperator.hf.space/health` to report the exact requested SHA;
a mismatch/unavailable health returns failure. A build may still be starting,
so retry the read-only health verification after readiness instead of treating
push success as a successful rollout. No merge or main-source push is required
for this explicitly authorized feature-branch snapshot.

## Local qualification

25 new tests cover documented detection, local/HF resolution priorities, missing
canonical secret, effective flags/masking/diagnostics, normal HTTP browser and
external API routing, CSRF, A2A Bearer/header/path auth, both MCP path transports,
wrong credentials, MCP missing-token refusal, actual HF entrypoint settings logic,
tracked/untracked dirty refusal, committed historical archive identity and exact
health-SHA comparison. API-message model execution is controlled in the auth test;
this proves authentication/dispatch, not a live model response. MCP downstream
protocol work is controlled; routing/auth and middleware are real.

Final broad selection: **532 passed, zero failed/skipped**, including all 25 new
checks and the existing 507-test Argus/reliability selection.

```bash
ARGUS_TEST_ARGUS_PYTHON=/workspace/venvs/argus/bin/python \
ARGUS_TEST_FOREMAN_PYTHON=/workspace/venvs/foreman/bin/python \
/workspace/venvs/openoperator/bin/python -m pytest \
  plugins/argus_supervisor/tests tests/test_hf_integration_auth.py \
  plugins/_chat_naming/tests plugins/_goal/tests \
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
/workspace/venvs/openoperator/bin/ruff check \
  scripts/deploy_hf_space.py tests/test_hf_integration_auth.py
bash -n docker/run/fs/exe/huggingface-entrypoint.sh
```

Compilation of changed Python modules, JavaScript syntax checks of the three
changed example scripts and whitespace checks also pass. Existing helper modules
have unrelated pre-existing Ruff findings; no blanket helper-lint pass is claimed.

## Live observations and blockers (17 October 2026)

Read-only public HF access succeeded. The SDK reports the Space RUNNING and HF
repository commit `644af8260f54d0646f4aa6edab5904efa4f1b1a9`. That is the **HF
repository SHA**, not a proven deployed GitHub source SHA. The committed
`openoperator-build.json` lookup returned 404. Live `/health` also returned 404,
so no running-source identity could be proven.

| Live probe | Observed result |
| --- | --- |
| Browser POST `/api/settings_get`, no login | 302; browser auth still enforced |
| POST `/api/settings_probe`, wrong key | 401 |
| POST `/api/api_message`, wrong key | 401 |
| A2A discovery, wrong X-API-KEY | 401 |
| MCP HTTP, wrong token path | 403 |
| Correct-token settings_probe/api_message | Not run: canonical credential unavailable |
| Authenticated A2A discovery/harmless task | Not run: canonical credential unavailable |
| Authenticated MCP SSE/HTTP negotiation | Not run: canonical credential unavailable |
| Requested source SHA deployed and health matched | Not performed/qualified |

The local environment has no `HF_TOKEN` or canonical integration-token binding.
Hugging Face SDK `whoami()` confirms `LocalTokenNotFoundError`, so public reads do
not establish write authentication. Canonical secret presence in the HF Space
cannot be established without authorized credential metadata access. No secret
value was requested in chat, generated, logged, retrieved from settings or changed
in HF. Secure optional cloud binding requirements have been saved for review;
that does not populate values, apply/publish configuration or configure HF secrets.

Deployment is authorized by this follow-up but blocked by those concrete
prerequisites. The operator must set `SPYNEL_AGENT_ZERO_API_KEY` in HF, bind a
write-scoped `HF_TOKEN` for upload, and bind the same canonical secret securely
for external acceptance tests. No upload/rebuild/restart/merge was performed.
After access is supplied, deploy the final committed SHA, wait for the exact health
SHA, then test correct-token API responses, one harmless A2A request and both MCP
transports; repeat wrong-token and browser-protection checks. Until then this is
locally qualified code with partial live negative-auth evidence, not a qualified
production deployment.
