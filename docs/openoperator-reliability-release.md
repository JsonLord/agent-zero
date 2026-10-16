# OpenOperator reliability release

## Source and architecture

Work branch: `jules-17409741302335967131-509964cf`; starting commit:
`c993b33b0392cb36aea54522fb95846f5e60b8a0`. Continue existing PR #27 against
`jules-4586832932011214207-6b36d6d5`; do not bypass that integration stack by
merging directly to `main`.

At inspection, PR #27 and draft PR #28 were open. PR #28's source was
`2f072b132a7e46bd6fb06c3e15a8b6583036885f`. Its `scripts/dspy_gepa.py` and
`agents/prompt-improver/` tree exactly match this branch. No second implementation
or merge was introduced. All pre-existing branch commits are retained.

The running Space's actual image/source revision is **unverified**: public HF
metadata/runtime requests were denied by the cloud network proxy. GitHub Actions
history is not proof of the running image. The latest recorded snapshot workflow
on `main` (`aaab39da5a757668099ca97470a6c1046a22f465`) was cancelled and the
concurrent legacy sync failed (runs 33669631891 and 33669632020). Reconcile the
live `/health` SHA and Space build history with the integration stack before
release; do not reset this branch to a guessed production revision.

Architecture:

- `tools/search_engine.py` calls `helpers/searxng.py` through the existing runtime
  bridge. The helper selects bounded search backends and the tool retains its
  normal `Response(..., break_loop=False)` contract.
- The chat naming monologue-end extension schedules plugin-local background work
  on AgentContext's persistent loop. Utility requests pass through the existing
  model configuration/LiteLLM pipeline; titles use existing chat persistence and
  state-dirty notifications.
- Spynel's skill dispatcher uses the shared deterministic resolver, then the
  existing authenticated internal API/goal delegate or trusted HTTPS gateway.
  Existing idempotency, revisions, attention states and adaptive polling remain.
- The Space image synchronizes `/git/agent-zero` to `/a0`, excluding `/a0/usr`,
  then runs the framework as UID 1000 on port 7860. DSPy stays in `/opt/venv-dspy`.

## Confirmed defects and repairs

### Search

Previously `_search` posted to fixed `localhost:55510` without explicit timeouts,
status validation or exception containment. `SearchEngine.searxng_search` awaited
it without catching failures; checking whether the returned value was an
Exception never handled a raised `ClientConnectorError`.

The previous Space entrypoint bypassed Supervisor and never launched SearXNG.
The Space image now verifies the base image's SearXNG source and dedicated venv,
installs pinned Gunicorn there, and makes that installation readable by uid 1000.
A missing installation fails the image build explicitly. On every Space startup,
`huggingface-services.py` launches one Gunicorn worker with four threads on
`127.0.0.1:55510`, with JSON search enabled and a fresh secret in private temporary
settings. It does not expose SearXNG publicly, require root/Redis/Supervisor, change
`/a0/usr`, or install packages at runtime. Installation belongs to the HF image
build; normal restarts only start the installed services.

The launcher probes `/config` for a valid engine registry for up to 30 seconds
before starting the UI. If readiness fails, the UI still starts with the existing
search fallbacks. SearXNG exits are logged and retried after five seconds. Container
termination stops both process groups; UI exit stops SearXNG and preserves the UI
exit status. Set `A0_SEARCH_BACKEND=auto` (or unset it) to use restored SearXNG;
a previously configured `tinyfish` backend continues to skip it.

Real local child-process tests cover readiness, failed startup, restart after
exit, UI failure and joint SIGTERM cleanup. The actual SearXNG image, upstream
search results and live memory usage remain unverified: no Docker build or HF
deployment was performed. After an authorized release, check Space logs for
`SearXNG ready`, request `http://127.0.0.1:55510/config` from inside the container,
and exercise a real search through OpenOperator. The public Space URL remains
the UI/API endpoint, not the search backend.

`A0_SEARCH_BACKEND=auto` tries SearXNG, then DuckDuckGo HTML. When
`TINYFISH_API_KEY` is set, it instead tries SearXNG, Tinyfish, then DuckDuckGo.
Explicit `searxng` or `duckduckgo` also falls back to Tinyfish when configured;
`tinyfish` selects it directly. Without the key, existing behavior is preserved. `A0_SEARXNG_URL` overrides the endpoint.
`A0_SEARCH_TIMEOUT_SECONDS` defaults to 15 seconds per backend (1–60), with a
3-second connection cap. Each failed provider consumes its own bounded timeout.
Use `duckduckgo` on a Space intentionally lacking SearXNG to avoid probing it.

Both adapters preserve titles, source URLs and snippets. HTTP errors, malformed
responses, DNS/connection failures and timeouts return safe reason codes and no
fabricated results. Legitimate empty results succeed; challenge pages do not.
Cancellation propagates and closes HTTP sessions. Tinyfish is opt-in through
`TINYFISH_API_KEY`, supplied by the operator in the HF Space environment.

Tinyfish uses GET `https://api.search.tinyfish.ai?query=…` for search and POST
`https://api.fetch.tinyfish.ai` with `{"urls":[url],"format":"markdown"}` for
HTTPS document content, authenticated with `X-API-Key`. These contracts match the
[official REST client](https://github.com/tinyfish-io/tinyfish-web-agent-integrations/blob/main/hermes/tinyfish_hermes/rest_client.py).
Fetch invokes Tinyfish immediately after the first native fetch failure, before
retry delays. This means immediate fallback invocation after failure, not zero
network latency. Native success and empty search results do not call Tinyfish.
HTTP/file documents, unsafe URLs, size-limit rejections, user intervention and
cancellation do not trigger remote fetching. Public URL validation applies to
requested and returned HTTPS URLs. Responses are bounded, TLS is verified,
provider redirects are disabled, and errors omit credentials and response bodies.
No additional package or inference service is needed. Live Tinyfish requests
remain untested because no API key is configured in this environment.

The pinned `duckduckgo-search==6.1.12` client hardcodes `verify=False`; this repair
does **not** use that client. The HTML adapter uses default verified aiohttp TLS,
environment proxy support and no redirects. No results obtained through the
unverified client were retained or used. Production HTTPS search remains untested.

### Naming

Commit `45654ad8` changed the browser rename modal's request timeout to **60,000
milliseconds**, not the provider timeout. It cannot by itself explain a backend
automatic-naming regression. `background=True` in `Agent.call_utility_model`
bypasses the rate-limiter callback; it does not create or retain background work.

Confirmed lifecycle defects: the extension did not retain tasks or bound the
entire utility operation, discarded once-mode results after any later user
message, and allowed always-mode results to overwrite manual titles. These
conditions are reproduced by the regression tests. Cancellation/garbage
collection or an unreachable live provider are not claimed as confirmed causes
of the specific production incident.

The plugin now retains one task per context, suppresses duplicate requests for
an unchanged sequence, supersedes pending always-mode requests, and lets
once-mode finish after later messages. Identity, sequence, title and revision
checks reject stale results. Manual saves and automatic compare-and-save are
serialized; context deletion cannot interleave with automatic persistence.

`automatic_naming_timeout_seconds` is scoped through the existing project/profile
configuration and UI, defaults to 45 seconds, and is clamped to 1–300. The budget
covers provider retries; this plugin adds no retries and changes no global model
timeout. Failures preserve titles and report safe diagnostic categories. Manual
retry remains available. Successful updates use existing persistence/sidebar
notification paths. The actual provider preset, authorization and timeout/retry
configuration of the live Space remain unverified.

### Spynel

The previous dispatcher recognized only explicit tokens and collapsed all
whitespace, including multiline/code payloads. It now also recognizes explicit
natural-language delegation against the active profile registry and trusted
`SPYNEL_SDK_*_URL`/`SPYNEL_AGENT_*_URL` registrations. Names, titles, normalized
multiword forms and conditional convenience aliases are supported. No profiles
or directories are created from user text.

The standalone resolver returns `dispatch`, `local` or `abstain`, a validated
target, canonical workspace path/candidates, recognition method, ambiguity and
the unchanged original message. Workspace candidates must exist beneath
`/a0/usr/workdir` after symlink resolution. Multiple targets or directories
abstain. Explicit profile+SDK gateway syntax keeps its precedence. Quotes,
examples, code blocks, URLs, partial names and filenames cannot select agents.
Natural dispatch preserves the original instruction and appends a canonical
workspace annotation when available; explicit dispatch removes only route tokens.

```bash
python scripts/spynel_resolver.py --resolve-only \
  'Have the reviewer inspect nodepad'
```

`--project` selects project-scoped discovery in the CLI; `SPYNEL_PROJECT` does so
in the dispatcher. `--workspace-root` is a read-only CLI testing override.

The final routing architecture has no classifier interface, endpoint integration,
model fallback or extra inference dependency. Explicit user tokens have highest
precedence. Deterministic matching resolves registered names and aliases; the
execution gate `prepare_route` validates files, folder references and configured
aliases before submission. The existing Spynel main interaction may select an
existing profile/SDK with `--profile` or `--sdk` and an existing `--workspace`;
these proposals are validated through the same gate and cannot override an
explicit, unknown or ambiguous target. No second model call is made for routing.
The read-only CLI accepts the same options. Legacy `resolve` retains the original
recognition corpus; only `prepare_route` authorizes actual dispatch.

Folder aliases can be existing confined symlinks or trusted
`SPYNEL_WORKSPACE_ALIASES` JSON mappings. Canonical workspace and file annotations
are delivered with the original multiline task. Missing files, escaping aliases,
and ambiguous directories abstain. The accompanying profile on a `/sdk` gateway
is also validated; a model-generated identifier cannot bypass registry checks.

### Local experiment reconciliation and persistent overrides

The supplied experiment summary reported 18/20 classifications, an inconsistent
table count and SDK outcomes conditional on registration. In this cloud machine,
all three experiment sources are absent: `/a0/usr/agents/spynel/`,
`/tmp/spynel_patch.diff`, and `/a0/usr/workdir/spynel_test_cases.md`. A row-by-row
comparison, reproduction of that score, and patch merge were **not** possible.
No local patch is claimed as merged. The useful edge-case requirements from the
supplied report were independently encoded in tests: ordinary URLs, registered
versus unregistered SDKs, real files/folders, canonical aliases, quotes/source
code, actual worker dispatch and multiline preservation.

The tracked bundled role/specifics and skill now describe the same routing
protocol, replacing the stale instruction to keep every token-free request
local. A core `_00_spynel_profile_guard.py` hook runs before the main model, and
the shared dispatcher performs the same read-only active-profile audit. Divergent
user, project or plugin routing prompts, context instructions, extension code or
skill files block routing with an explicit reconciliation message. Identical
copies and metadata-only title/avatar edits are allowed. No user files are
changed or deleted. This intentionally prevents a retained experimental profile
from silently taking precedence after redeployment.

```bash
python scripts/spynel_resolver.py --check-profile
# For a scoped profile, also supply --project <existing-project>.
```

A blocked audit exits nonzero. Before a future release, an authorized operator
must back up, review and explicitly reconcile any listed persistent overrides;
the cloud test cannot prove that the live Space has no such overrides. No
migration or removal of `/a0/usr/agents/spynel` has been performed. The amendment
leaves NeuralMind, SearXNG/search and Parallel MCP requirements unchanged.

The labeled deterministic corpus includes explicit/natural routes, aliases,
nested workspaces, collisions, ambiguity, quoted/code/URL examples, unknown
targets, and multilingual abstention/explicit routes. The original 62 labeled
recognition cases are retained; extra tests exercise the final execution gate.
Initial confusion cases (filename suffixes, partial aliases, multiple targets)
were corrected; all labeled cases now pass.

### Release control

Both HF workflows previously triggered on the same main commit with the same
cancel-in-progress group. That allowed the history mirror to cancel the clean
snapshot deployment. Only `deploy-huggingface-space.yml` now uploads; its manual
runs are guarded to `refs/heads/main`. The legacy workflow is manual and prints
an explanation without accessing credentials or uploading.

Snapshots write `openoperator-build.json` with the GitHub `source_sha`, using the
existing `/health` provenance contract. CI includes the new reliability suites.
Two stale test fixtures were repaired: the HTTP-auth test app now registers the
index endpoint present in the real app and checks decoded redirect semantics;
the sidebar assertion accepts the existing multiline API call formatting.
No authentication/CSRF implementation or assertions were disabled.

## Validation and resources

441 selected tests passed, zero failed/skipped. The suite includes the Tinyfish
REST contract, immediate fallback, document dispatch, cancellation, URL validation
and credential-safe failure tests. This includes search HTTP
failures through real loopback requests and the ordinary tool response; naming
success, delay, errors, cancellation, manual races, context deletion, scoped
configuration, concurrent chats and persistence; the **real Agent monologue and
response tool completing while utility naming remains pending**; deterministic
routing, final selection validation, profile-override guards, real local authenticated
API/AgentContext/response-tool/polling dispatch, A2A, goal delegation, authentication/CSRF,
profiles, HF defaults, Colab, Repository Manager and DSPy/GEPA offline contracts.
Full deployment/image tests and live external agent/model calls were not run.

The exact selected pytest command is in the PR validation description. The
original 62 recognition rows and existing dispatch regressions are preserved;
obsolete classifier-specific tests are replaced by no-classifier/no-network and
registry-validation regressions. Four authenticated local worker cases exercise
actual profile selection, native curl, task submission, execution and polling
with controlled model responses; 9 rejection cases create no worker and a
separate wrong-key case verifies authentication. Ruff
checks for changed reliability modules/tests, compile checks, shell syntax and
`git diff --check` pass. Local UI startup returned HTTP 200 for `/` and
`{"status":"ok", "sha": ...}` from `/health` on loopback. A real unavailable
search returned structured failure without an escaping traceback.

The Space adds pinned Gunicorn in the existing SearXNG venv and one private
SearXNG worker with four threads. Its actual RAM cost still needs image/runtime
measurement. No database or public port is added. Search
adds bounded HTTP fallbacks plus modest HTML parsing per request; no per-query
process is spawned. Naming retains at most one task per chat (default lifetime
45 seconds) and a brief persistence lock. Production CPU/RAM were not measured;
no production performance numbers are claimed. Startup launches private SearXNG but adds no new model load. DSPy/GEPA job ownership and its separate environment are unchanged.

The local backend/UI development environment uses a CPU-only Python virtualenv.
The full optional document stack's initial installation backtracked into an old
scikit-learn source build requiring unavailable clang. A backend subset, Whisper,
LiteParse and test tools installed successfully. Optional document ingestion/TTS
were not validated. Browser provisioning is blocked by `cdn.playwright.dev`
network policy; offline embedding preload has no cached model. UI and selected
backend tests work despite these optional-feature limits. Fresh full-image
package resolution remains part of the later authorized build acceptance.

## Future deployment acceptance (not executed)

1. Verify the live source SHA and preserve the current image reference and a
   recoverable `/a0/usr` backup using the operator's existing backup procedure.
   Review PR #27/#28 overlap and the integration stack; do not duplicate GEPA.
2. Review and merge through the intended integration branch. Authorize the
   eventual main-branch deployment separately: merging to `main` still triggers
   the single snapshot publisher and HF builds the image.
3. Verify the HF build contains existing runtime dependencies and model/browser
   artifacts at image-build time. Keep non-root execution, only port 7860,
   `A0_CLOUDFLARE_DISABLED=true`, `PIP_NO_INDEX=1`, `/a0`, `/git/agent-zero` and
   the `/a0/usr` rsync exclusion. No Dockerfile/entrypoint changes are required
   by these repairs. Do not install dependencies during Space startup.
4. From an authorized operator environment, run the existing smoke script with
   credentials supplied securely by existing environment bindings:

   ```bash
   export EXPECTED_OPENOPERATOR_SHA='<approved merged GitHub SHA>'
   python scripts/smoke_hf_openoperator.py
   ```

   Verify `/health` reports that SHA, authenticated API/A2A `message/send` and
   `tasks/get` work, malformed calls fail cleanly, and blocking mode remains.
   Run a real remote-agent and internal Spynel request, `/goal`, Colab health,
   and a small existing DSPy/GEPA validation job. The offline tests do not prove
   those external services or credentials are usable.
5. Exercise Search Engine with a real query. With `A0_SEARCH_BACKEND=auto`,
   intentionally unavailable SearXNG must fall back or report structured
   unavailability; with `duckduckgo`, SearXNG is intentionally unused. If a remote
   SearXNG is configured, verify its reachability and TLS independently. With
   `TINYFISH_API_KEY` configured, verify search and public HTTPS document fallback
   against Tinyfish after an intentional native failure; never put the key in logs.
6. Start a new chat: verify automatic title persistence and sidebar updates while
   the main model remains responsive. Rename it manually while a delayed title
   is pending; verify the manual title wins. Test once/always/disabled settings.
7. Run the read-only Spynel profile audit with the framework interpreter before
   using Spynel, including any active project scope. If blocked, preserve and
   explicitly reconcile the reported persistent overrides. Create a harmless test directory through the usual workspace workflow, then
   use the read-only resolver with natural and explicit routes. Test a symlink
   escape and ambiguous targets; neither may be dispatched automatically.
8. Check logs, memory, only one public listener, preserved profiles/model settings,
   persistent working directories and existing secrets before accepting release.

## Rollback

After separate authorization, restore the recorded previous application image
or redeploy the prior reviewed source snapshot through the one authoritative
publisher. Do not use the legacy history mirror, force-push a production branch,
or run destructive synchronization against user state. Keep `/a0/usr` and
existing secrets/model settings in place; verify `/health`, auth/A2A, user data
and the prior functionality after rollback. These repairs introduce no database
migration. Revert the individual repair commits on an integration branch for a
source-level rollback and review before a later main deployment.

## Boundaries honored

No local Docker build; no HF upload, Space restart, rebuild or workflow trigger;
no production credential changes; no production-branch push; no public listener
added; no `/a0/usr` reset. This is a code-review candidate with pending live
source reconciliation and deployment acceptance, not a deployed Space.
