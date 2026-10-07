# OpenOperator Hugging Face Deployment Contract

Target Space:

```text
Leon4gr45/openoperator
https://huggingface.co/spaces/Leon4gr45/openoperator
```

Source repository:

```text
https://github.com/JsonLord/agent-zero
```

Current integration PR:

```text
https://github.com/JsonLord/agent-zero/pull/26
```

This document is the deployment contract for OpenOperator.

The purpose is to ensure that Hugging Face always runs one complete, internally consistent Agent Zero/OpenOperator revision rather than a partial copy of selected files.

The Hugging Face Space must contain the **exact tested source revision** including:

- OpenOperator HF runtime changes;
- specialist Agent Zero profiles;
- shared skills;
- Spynel;
- `/goal`;
- model/provider defaults;
- API authentication;
- settings hardening;
- memory behavior;
- Paperclip skills;
- Colab helper;
- tests and smoke tooling required for deployment verification.

Do not manually copy isolated profile folders into an older Space checkout.

---

# 1. Deployment invariant

The primary deployment invariant is:

```text
final green GitHub SHA
        ==
HF Space source snapshot
        ==
/git/agent-zero source
        ==
/a0 runtime application code
```

while mutable runtime state remains separate:

```text
/a0/usr
```

Application code must be refreshed on every new image build.

User/runtime state must not be deleted simply because application code is updated.

---

# 2. Deployment source

Deploy only a Git commit that has passed the repository's OpenOperator integration workflow.

Required before deployment:

```text
OpenOperator integration: SUCCESS
0 failing project-specific regression tests
```

Do not deploy a red commit.

Record the exact GitHub source SHA before creating the Space snapshot.

Example:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
```

Do not use an unqualified moving branch such as `main`, `HEAD`, or a PR ref as the deployment identity after the build begins.

The deployment should always be attributable to one immutable commit SHA.

---

# 3. Files that MUST be deployed

Deploy the complete source snapshot from the selected commit.

At minimum the deployed source must include:

```text
Dockerfile
docker/
helpers/
api/
agents/
skills/
plugins/
scripts/
prompts/
webui/
tests/
requirements.txt
requirements.dev.txt
run_ui.py
preload.py
```

Do not create an allowlist that accidentally omits newly added application files.

Preferred deployment method:

```text
git archive <exact-SHA>
        ->
clean HF Space snapshot
        ->
push complete snapshot to Leon4gr45/openoperator
```

The existing repository deployment helper may be used:

```bash
python scripts/deploy_hf_space.py \
  --space Leon4gr45/openoperator \
  --sha "$SOURCE_SHA"
```

The script must deploy the exact requested commit rather than silently substituting another revision.

---

# 4. Files/state that must NOT be taken from an old deployment

Do not preserve stale application source from an older Space revision.

In particular, do not let an old:

```text
/a0/run_ui.py
```

prevent new application code from being installed.

Do not preserve old copies of:

```text
/a0/agents
/a0/skills
/a0/plugins
/a0/helpers
/a0/api
/a0/webui
```

when a new image is built.

These are application code and must come from the new deployment source.

---

# 5. Mutable state that MUST remain separate

Do not wipe user/runtime state when synchronizing application code.

Protect:

```text
/a0/usr
```

including, where present:

```text
/a0/usr/settings.json
/a0/usr/agents
/a0/usr/projects
/a0/usr/plugins/_goal/goals
/a0/usr/workdir
/a0/usr/knowledge
```

The source synchronization contract is:

```text
replace/update application code
preserve /a0/usr
```

If an exact-mirror synchronization mechanism such as `rsync --delete` is used, `/a0/usr` must be explicitly excluded.

Never run a broad deletion against `/a0` without excluding user state.

---

# 6. Runtime source synchronization

The Space image currently stages repository source under:

```text
/git/agent-zero
```

and Agent Zero runs from:

```text
/a0
```

The deployment must deterministically synchronize source from:

```text
/git/agent-zero
```

to:

```text
/a0
```

before `run_ui.py` starts.

Required invariant:

```text
/git/agent-zero/agents/reviewer
        ->
/a0/agents/reviewer
```

and equivalent for all application files.

Do not use the former behavior:

```bash
if [ ! -f /a0/run_ui.py ]; then
    copy source
fi
```

because an inherited/stale `/a0/run_ui.py` can prevent new source from being deployed.

If `rsync` is used, ensure `rsync` is actually installed in the image.

Do not depend on an undeclared binary.

A valid approach is conceptually:

```bash
rsync -a --delete \
  --exclude='/usr' \
  /git/agent-zero/ \
  /a0/
```

provided that:

- `rsync` is guaranteed to exist;
- `/a0/usr` is preserved;
- any other legitimate runtime state is explicitly excluded;
- the operation is tested in the actual container build/runtime path.

A dependency-free copy implementation is also acceptable if it guarantees equivalent semantics.

---

# 7. Required built-in profiles

The runtime must contain and natively discover all of these profiles:

```text
developer
hacker
spynel

reviewer
tester
tiny-coder
debugger
integrator
frontend-qa
evals
shipper
launch
performance
security
refactorer
maintainer
data-engineer
docs
```

Expected runtime paths include:

```text
/a0/agents/developer
/a0/agents/hacker
/a0/agents/spynel
/a0/agents/reviewer
/a0/agents/tester
/a0/agents/tiny-coder
/a0/agents/debugger
/a0/agents/integrator
/a0/agents/frontend-qa
/a0/agents/evals
/a0/agents/shipper
/a0/agents/launch
/a0/agents/performance
/a0/agents/security
/a0/agents/refactorer
/a0/agents/maintainer
/a0/agents/data-engineer
/a0/agents/docs
```

Each profile must contain valid native Agent Zero metadata, such as:

```text
agent.yaml
```

and its required prompt files.

Do not maintain a second OpenOperator-only profile registry.

Native discovery is authoritative.

Verify using the canonical Agent Zero discovery path:

```python
subagents.get_available_agents_dict(None)
```

---

# 8. Required specialist behavior

The deployed profile prompts must contain the current final behavior contracts.

## Developer

Must include:

```text
delegation-first behavior
specialist selection
parallel bounded delegation
/goal ownership
smart polling
think-ahead behavior while workers run
evidence synthesis
```

## Hacker

Must include:

```text
parallel investigation
hypothesis swarm behavior
debugger/security/integrator delegation
/goal ownership
```

## Tester

Must include:

```text
local/container/browser/Colab/DGX decision policy
test evidence contract
```

## Tiny Coder

Must include:

```text
bounded task packet
small patch preference
small-model-compatible behavior
ABSTAIN/escalate semantics
```

## Reviewer

Read-only by default.

## Shipper

Must preserve production approval gates.

## Launch

Must remain separate from production authorization.

Do not deploy stale prompt versions from older branches.

---

# 9. Required global skills

The runtime must contain the current shared skills, including at least:

```text
api-contract
benchmark
brag
colab-execute
compile-check
context-packager
dependency-doctor
diff-self-review
docker-diagnose
failure-to-next-patch
git-worktree
github-pr
golive
hf-space
patch-small
playwright
repo-map
secret-safe-env
spec-check
symbol-locator
task-slicer
test-evidence
test-targeted
```

Expected runtime root:

```text
/a0/skills
```

Verify native skill discovery after the Space starts.

---

# 10. Required Spynel-local skills

Spynel also contains profile-local skills that must survive deployment:

```text
/a0/agents/spynel/skills/spynel-dispatch
/a0/agents/spynel/skills/paperclip-board-manager
```

These are separate from the global `/a0/skills` inventory.

Deployment acceptance must explicitly verify both.

Do not assume a successful global skills catalog proves the Spynel-local skills exist.

---

# 11. `/goal` subsystem

The deployed revision must include the `_goal` plugin and its final state semantics.

Required deployment content includes:

```text
/a0/plugins/_goal
```

The deployed goal engine must retain:

```text
durable goal state
semantic progress revisions
bounded adaptive polling
attention states
dependency validation
idempotency scoping
resource limits
parent/child goals
restart reconciliation
evidence-based completion
```

Goal state under:

```text
/a0/usr/plugins/_goal/goals
```

is mutable user/runtime state and must not be wiped by application-code synchronization.

---

# 12. Spynel routing

The deployed Spynel profile must preserve routing semantics:

```text
no token
    -> local execution

@profile
    -> existing internal Agent Zero profile
       OR registered external agent

/sdk
    -> configured external SDK/gateway
```

Unknown profiles must fail explicitly.

Routing must never auto-create an unknown profile.

External target URLs must come from configuration, not raw user-provided arbitrary URLs.

---

# 13. Required environment variables and secrets

Keep secrets in Hugging Face Space Secrets.

Do not commit actual secret values.

## Main OpenAI-compatible model

Variables/secrets:

```text
COMPATIBLE_URL
COMPATIBLE_MODEL
BLABLADOR_API_KEY
```

Contract:

```text
COMPATIBLE_URL
    = OpenAI-compatible model API base URL

COMPATIBLE_MODEL
    = actual model or alias used for main chat

BLABLADOR_API_KEY
    = authentication credential for that model endpoint
```

`COMPATIBLE_URL` must NOT point to the Hugging Face MCP endpoint.

It must point to an actual OpenAI-compatible inference service.

The model path must support the API route expected by LiteLLM/OpenAI-compatible transport.

---

# 14. Agent Zero internal API key

Secret:

```text
SPYNEL_AGENT_ZERO_API_KEY
```

Purpose:

```text
Spynel/internal authenticated Agent Zero API calls
```

It is not:

```text
a model API key
a Hugging Face token
an MCP OAuth token
```

The deployed runtime must accept this exact secret through:

```text
X-API-KEY
```

for the protected Agent Zero internal API.

The key must remain masked in settings/public responses.

---

# 15. Hugging Face token

Secret:

```text
HF_TOKEN
```

Use only where required for:

```text
deployment
private Hugging Face resources
Hugging Face MCP authentication
```

Do not reuse it as:

```text
BLABLADOR_API_KEY
SPYNEL_AGENT_ZERO_API_KEY
```

Never print the token in logs.

---

# 16. Hugging Face MCP

Hugging Face MCP is a tool/backend integration and is independent from the main LLM provider.

MCP endpoint:

```text
https://huggingface.co/mcp
```

OAuth login:

```text
https://huggingface.co/mcp?login
```

Do not set:

```text
COMPATIBLE_URL=https://huggingface.co/mcp
```

The request flow must remain:

```text
user message
    ->
main LLM succeeds
    ->
agent selects MCP tool
    ->
Hugging Face MCP request
```

If the main LLM receives HTTP 403 before tool selection, debug the main model/provider configuration first.

---

# 17. HF runtime requirements

The Space must run as:

```text
UID 1000
GID non-root
host 0.0.0.0
port 7860
dockerized production mode
```

Required launch behavior:

```text
run_ui.py --dockerized=true
```

Required environment:

```text
A0_CLOUDFLARE_DISABLED=true
SPYNEL_AGENT_ZERO_URL=http://127.0.0.1:7860
```

Do not expose new public ports.

Do not start:

```text
SSH
cron
Cloudflare tunnel
privileged supervisor stack
```

for the HF Space runtime.

Hugging Face already provides the public HTTPS edge.

---

# 18. Root-password behavior

HF runs non-root.

The runtime must report:

```text
root_password_supported=false
```

and must not call:

```text
chpasswd
```

under UID 1000.

An empty or placeholder root-password setting must remain a no-op.

The UI must not imply root-password management is supported when it is not.

---

# 19. RFC/runtime behavior

HF production must be recognized as:

```text
dockerized=true
development=false
```

Normal chat/prompt include behavior must not attempt development-only RFC calls.

The runtime must not require an RFC password for normal production chat.

---

# 20. Source SHA identity

The running Space must expose the exact deployed GitHub source SHA.

Preferred mechanism:

```text
OPENOPERATOR_SOURCE_SHA=<exact GitHub SHA>
```

or an immutable source metadata file generated from the deployment snapshot.

Do not rely solely on:

```text
.git
```

because `.git` is excluded from the Docker build context.

`GET /health` should return conceptually:

```json
{
  "status": "ok",
  "sha": "<exact deployed GitHub SHA>"
}
```

The SHA must not be blank in a production deployment.

The deployment helper must arrange for the SHA to be available to the image/runtime.

---

# 21. HF Space metadata

The deployment snapshot must contain Hugging Face Space README metadata compatible with Docker Spaces:

```yaml
---
title: OpenOperator
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---
```

Preserve valid existing metadata when already present.

Do not accidentally replace Space SDK configuration with Gradio or Static.

---

# 22. Build-time profile assertion

Before runtime acceptance, verify all required built-in profiles exist.

The build/startup validation should fail clearly if required profiles are missing.

Verify both:

```text
filesystem presence
native discovery
```

Filesystem-only validation is insufficient.

---

# 23. Build-time skill assertion

Verify global required skills exist under:

```text
/a0/skills
```

and verify the two Spynel-local skills separately:

```text
/a0/agents/spynel/skills/spynel-dispatch
/a0/agents/spynel/skills/paperclip-board-manager
```

Do not conflate global skill discovery with profile-local skill discovery.

---

# 24. Post-deployment startup signature

A fresh deployment should show current synchronization behavior.

Do not accept an old startup signature such as:

```text
Copying files from /git/agent-zero to /a0...
```

if the current deployment implementation should instead use deterministic synchronization.

The startup log should make it obvious which deployment path is active.

If logs indicate old copy behavior, treat the Space as stale and redeploy the correct revision before debugging profile discovery.

---

# 25. Post-deployment health acceptance

After the HF build finishes:

```bash
curl -fsS https://leon4gr45-openoperator.hf.space/health
```

Expected:

```text
status = ok
sha = exact expected GitHub SHA
```

Fail acceptance if the SHA is absent or mismatched.

---

# 26. Full smoke acceptance

Run:

```bash
export OPENOPERATOR_BASE_URL=https://leon4gr45-openoperator.hf.space
export SPYNEL_AGENT_ZERO_API_KEY='<secret from environment>'
export HF_TOKEN='<only if required>'

python scripts/smoke_hf_openoperator.py --full
```

Do not place secrets directly into committed scripts.

The full smoke must require PASS for:

```text
health
deployed SHA
settings
dockerized production runtime
non-root runtime
root-password unsupported
API key accepted and masked
compatible provider configured
settings save/reload
plain chat
memory extension
specialist profiles
Spynel
required global skills
Spynel local skills
unknown profile rejection
profile-create protection
reviewer /goal delegation
Paperclip skill
```

Any required check that was not executed must not silently disappear from the mandatory result set.

---

# 27. Specialist profile acceptance

The live Agent Zero/OpenOperator profile catalog must contain all required profiles.

Verify through the authenticated native API.

Also verify that a representative profile can actually initialize:

```text
reviewer
tester
tiny-coder
debugger
shipper
```

Catalog presence alone is not enough.

The selected profile must load its own native prompt/config rather than silently falling back to `agent0`.

---

# 28. Spynel live acceptance

Test:

```text
@reviewer Review the current runtime configuration.
```

or equivalent internal delegation through the authenticated API.

Expected:

```text
profile = reviewer
fresh context created
goal created if goal mode used
finite polling
terminal result or explicit attention state
```

Test unknown profile safety:

```text
@definitely-not-real
```

Expected:

```text
explicit failure
no context created
no profile created
```

---

# 29. `/goal` live acceptance

Create one harmless reviewer goal.

Example objective:

```text
Inspect runtime mode and return a read-only summary.
```

Require:

```text
context_id
goal_id
semantic polling
terminal result
```

Do not consider goal creation alone sufficient.

---

# 30. Main LLM acceptance before MCP testing

Before testing any external MCP integration, plain chat must work.

Test:

```text
hi
```

Expected:

```text
main model call succeeds
normal Agent Zero response returned
```

If the trace fails at:

```text
Agent.monologue
 -> call_chat_model_turn
 -> LiteLLM
 -> HTTP 403
```

then the MCP tool has not been reached.

Debug:

```text
COMPATIBLE_URL
COMPATIBLE_MODEL
BLABLADOR_API_KEY
```

first.

---

# 31. Model-provider 403 diagnostic

An HTML error such as:

```html
403 Forbidden
openresty
```

usually means the request is being rejected by the model endpoint's HTTP gateway/proxy before a normal OpenAI-compatible response is returned.

Check:

```text
correct base URL
correct /v1 path behavior
correct bearer/auth header
correct model alias
provider access controls
```

Do not debug Hugging Face MCP until main chat succeeds.

---

# 32. Memory acceptance

After successful plain chat, verify the logs do not contain unexpected:

```text
Memorize memories extension error
```

The smoke must fail if normal configured chat produces this error unexpectedly.

Do not silence the warning merely to obtain a green deployment.

---

# 33. Settings acceptance

Use the authenticated safe settings probe.

Verify:

```text
settings read succeeds
API token is masked
runtime dockerized=true
development=false
uid/gid non-root
root_password_supported=false
main compatible provider configured
```

Also perform one reversible safe settings mutation:

```text
read current time format
change
save
reload
verify
restore
reload
verify
```

Do not mutate secrets during smoke testing.

---

# 34. UI acceptance

Inside the running OpenOperator UI—not the Hugging Face admin settings page—verify the Agent/Profile selector includes:

```text
Developer
Hacker
Spynel
Reviewer
Tester
Tiny Coder
Debugger
Integrator
Frontend QA
Evals
Shipper
Launch
Performance
Security
Refactorer
Maintainer
Data Engineer
Docs
```

Selecting representative profiles must not cause console/network errors.

Also verify dark/light icon contrast on the previously affected surfaces.

---

# 35. Do not use HF admin settings as profile evidence

This page:

```text
https://huggingface.co/spaces/Leon4gr45/openoperator/settings
```

is Hugging Face infrastructure administration.

It is not expected to display Agent Zero profiles.

Profiles must be visible in:

```text
the running OpenOperator / Agent Zero application UI
```

and native Agent Zero profile APIs.

---

# 36. Deployment failure rules

Treat deployment as FAILED if any of the following occurs:

```text
Space starts old source revision
/health SHA absent or mismatched
specialist profile missing
Spynel-local skill missing
main LLM 403
settings probe fails
API key rejected
runtime identified as development
root-password code attempts chpasswd
plain chat fails
reviewer goal cannot execute
```

Do not mark the Space healthy merely because:

```text
Uvicorn starts
/health returns 200
```

Application startup is necessary but not sufficient.

---

# 37. Deployment rollback

Before replacing a known working deployment, record:

```text
previous GitHub SHA
previous HF Space commit
```

If the new deployment fails acceptance, restore the prior complete source snapshot.

Do not hot-fix individual files inside the failed HF image.

Repair the source branch, create a new tested SHA, then redeploy one coherent revision.

---

# 38. Deployment completion report

Jules must return a deployment report with:

## Source

```text
GitHub source SHA:
HF Space commit:
health-reported SHA:
all match: YES/NO
```

## CI

```text
OpenOperator integration:
passed:
failed:
```

## Runtime

```text
uid:
gid:
dockerized:
development:
root_password_supported:
```

## Model

```text
provider:
model:
api_base:
plain chat: PASS/FAIL
```

Do not print API keys.

## Profiles

List the exact discovered profile names.

## Global skills

List required global skills and PASS/FAIL.

## Spynel-local skills

```text
spynel-dispatch: PASS/FAIL
paperclip-board-manager: PASS/FAIL
```

## Goal

```text
reviewer goal creation:
polling:
terminal result:
```

## Settings

```text
read:
save:
reload:
restore:
```

## Memory

```text
normal chat memory extension:
PASS/FAIL
```

## UI

```text
profile selector:
dark theme:
light theme:
```

## Final verdict

Use exactly one:

```text
DEPLOYMENT ACCEPTED
```

or:

```text
DEPLOYMENT REJECTED
```

Do not declare acceptance if any mandatory item is unverified or failing.

---

# 39. Final principle

The Hugging Face Space is not a separate manually curated fork of OpenOperator.

It is a deployment artifact of one exact tested GitHub revision.

The deployment standard is:

> One green GitHub SHA in, one complete HF Space revision out, with application code synchronized deterministically, `/a0/usr` preserved, required profiles and skills discoverable, main chat functional, and the live SHA provable through health/acceptance checks.
