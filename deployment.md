# OpenOperator Hugging Face Space Deployment & Acceptance Contract

## 1. System Invariants

OpenOperator enforces a strict separation between immutable application code and persistent user/runtime state:

```text
green GitHub SHA
       ==
HF snapshot
       ==
/git/agent-zero
       ==
/a0 application code
```

while:

```text
/a0/usr
```

remains persistent, mutable user state containing settings, goals, workdirs, logs, and `usr/.env`.

---

## 2. Exact Application Code Synchronization

During container startup (`docker/run/fs/ins/copy_A0.sh`), exact application code is synchronized:

```bash
rsync -a --delete --no-owner --no-group --exclude='/usr' /git/agent-zero/ /a0/
```

- Application code in `/a0` is kept perfectly in sync with the build snapshot `/git/agent-zero`.
- Obsolete application files removed from newer commits are pruned from `/a0`.
- The user directory `/a0/usr` (and all subdirectories `/a0/usr/*`) is strictly excluded from deletion or overwrite.

---

## 3. Deployment Secret Mapping & Bridge

Hugging Face Space Secrets arrive as process environment variables. Upon application startup, `helpers/runtime_secrets.py` normalizes and bridges these secrets into `/a0/usr/.env` with strict `0600` permissions.

### Secret Mapping Table

| Space Secret Variable | Canonical Runtime Variable(s) | Purpose |
|---|---|---|
| `SPYNEL_AGENT_ZERO_API_KEY` | `SPYNEL_AGENT_ZERO_API_KEY` | Agent Zero internal API authentication (`X-API-KEY`) |
| `HUGGINGFACE_TOKEN` | `HF_TOKEN` | Hugging Face CLI (`hf`) & remote Hugging Face MCP authorization |
| `GITHUB_PAT` | `GH_TOKEN`, `GITHUB_TOKEN` | GitHub repository inspection, PR management & Git operations |

### Model Provider Secrets

| Environment Variable | Canonical Runtime Setting | Purpose |
|---|---|---|
| `COMPATIBLE_URL` | `chat.api_base` | OpenAI-compatible LLM endpoint URL |
| `COMPATIBLE_MODEL` | `chat.name` | OpenAI-compatible model name |
| `BLABLADOR_API_KEY` | `API_KEY_OTHER` | Model API key stored securely outside presets in `.env` |

### Critical Credential Distinctions

- `HF_TOKEN` (Hugging Face token) is **NOT** the LLM model API key.
- `HF_TOKEN` is **NOT** the Spynel API key (`SPYNEL_AGENT_ZERO_API_KEY`).
- `GITHUB_PAT` is **NOT** the Hugging Face token.

### Secret Hygiene & Rotation Rules

1. Space process environment variables override stale persisted values in `usr/.env` upon container restart.
2. Secret values are **NEVER** printed, logged, returned in `/health`, or exposed via settings APIs.
3. Diagnostic endpoints report boolean presence status only (`{"spynel_api_key": true, "hf_token": true, "github_token": true}`).

---

## 4. Deployed Source SHA Identity

Every deployment snapshot includes `/openoperator-build.json` containing:

```json
{
  "source_sha": "<full-github-commit-sha>"
}
```

The application exposes this identity via:

- `GET /health` -> `{"status": "ok", "sha": "<full-github-commit-sha>"}`

Acceptance smoke testing compares `GET /health`'s reported SHA against the target green commit SHA.

---

## 5. Hugging Face MCP Client Integration

OpenOperator connects to Hugging Face's official remote MCP server as a client:

- **Endpoint**: `https://huggingface.co/mcp`
- **Transport**: Streamable HTTP (`type: "streamable-http"`)
- **Header Configuration**: `"Authorization": "Bearer ${ENV:HF_TOKEN}"`

### Safe Secret Interpolation

- `helpers/mcp_handler.py` substitutes `${ENV:VAR_NAME}` placeholders in memory at request time.
- Placeholders match `^[A-Z_][A-Z0-9_]*$` strictly. Arbitrary code execution or `eval` is prohibited.
- Serialized `settings.json`, UI outputs, and logs preserve the literal placeholder `${ENV:HF_TOKEN}` and never log expanded secret tokens.
- No local MCP daemon or additional listening port is executed (only public port `7860`).

---

## 6. Modern `hf` CLI Tooling

The modern `hf` CLI (`huggingface_hub[cli]`) is installed at image build time in `/opt/venv-a0/bin/hf`:

- Available on system `PATH`.
- Authenticates seamlessly via `HF_TOKEN` in environment.
- Commands utilized by OpenOperator:
  - `hf auth whoami`
  - `hf spaces info OWNER/SPACE`
  - `hf spaces logs OWNER/SPACE`
  - `hf spaces logs --build OWNER/SPACE`
  - `hf spaces secrets list OWNER/SPACE`

---

## 7. Specialist Profile Organization

OpenOperator includes 19 native specialist profiles under `/a0/agents/`:

1. `developer` - Software architecture & master orchestration
2. `hacker` - Security research & parallel hypothesis testing
3. `spynel` - External API routing & task dispatch
4. `reviewer` - Read-only code & spec review
5. `tester` - Test suite execution & evidence verification
6. `tiny-coder` - Bounded 1-3 file patch implementation
7. `debugger` - Failure localization & falsifiable hypotheses
8. `integrator` - API contracts & protocol verification
9. `frontend-qa` - UI contrast & browser behavior verification
10. `evals` - Benchmark evaluation & performance metrics
11. `shipper` - Release preparation & production approval gate
12. `launch` - Launch storyboard & release notes
13. `performance` - Concurrency profiling & latency analysis
14. `security` - Surface security auditing & credential checks
15. `refactorer` - Structural changes & technical debt reduction
16. `maintainer` - Dependency updates & environment maintenance
17. `data-engineer` - Data pipeline & schema engineering
18. `docs` - Verified technical documentation
19. `repository-manager` - Git, GitHub PR, and Hugging Face Space management

### `repository-manager` Policy

- **Default Mode**: Read-only inspection (`git status`, `git log`, `git diff`, `hf spaces info`, `hf spaces logs`, `hf spaces secrets list`).
- **Mutation Policy**: Pushes, branch deletions, PR merges, Space variable changes, and deployments require explicit authorization.

---

## 8. Deployment & Acceptance Procedure

### Deployment Execution

To deploy a verified green GitHub commit SHA to Hugging Face Space `Leon4gr45/openoperator`:

```bash
export HF_TOKEN="<write-scoped-hf-token>"
python3 scripts/deploy_hf_space.py --space Leon4gr45/openoperator --sha <green-commit-sha>
```

### Live Acceptance Verification

Once the Space rebuilds, run the acceptance smoke test:

```bash
export SPYNEL_AGENT_ZERO_API_KEY="<deployment-secret>"
export EXPECTED_OPENOPERATOR_SHA="<green-commit-sha>"
python3 scripts/smoke_hf_openoperator.py --mode full --expected-sha <green-commit-sha>
```

Required Live Verification Checklist:

- [x] Health status == PASS (`GET /health`)
- [x] Deployed SHA matches expected GitHub commit SHA
- [x] Specialist Profiles == PASS (all 19 profiles discoverable)
- [x] Required Skills == PASS (all 23 skills present)
- [x] Spynel Routing == PASS (`@repository-manager`, `@reviewer`, etc.)
- [x] Goal Delegation == PASS (`/goal` execution with specialist profile)
- [x] Unknown Profile Safety == PASS (404 on unknown profiles)
- [x] API Token Masking == PASS (`mcp_server_token == "************"`)
