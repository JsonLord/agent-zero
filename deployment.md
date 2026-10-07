# OpenOperator Hugging Face Space Deployment Contract

## 1. Core Invariants

The OpenOperator deployment maintains a strict boundary between immutable application code and mutable user/runtime state:

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

remains persistent, mutable user state (including `settings.json`, `usr/.env`, goals, workdirs, and logs).

## 2. Synchronization Policy

During container initialization (`docker/run/fs/ins/copy_A0.sh`):

- Application source is deterministically synchronized from `/git/agent-zero` to `/a0`.
- The user directory `/a0/usr` is strictly excluded from deletion or overwrite.
- Stale application files removed in newer commits are pruned from `/a0` while preserving user state.

## 3. Deployment Secret Mapping Table

Space secrets provided by Hugging Face process environment variables are mapped to canonical runtime environment variables and bridged into `/a0/usr/.env` with `0600` permissions upon startup:

| Space secret | Canonical runtime name | Purpose |
|---|---|---|
| `SPYNEL_AGENT_ZERO_API_KEY` | `SPYNEL_AGENT_ZERO_API_KEY` | Agent Zero internal API (`X-API-KEY`) |
| `HUGGINGFACE_TOKEN` | `HF_TOKEN` | Hugging Face CLI (`hf`) and Hugging Face MCP authorization |
| `GITHUB_PAT` | `GH_TOKEN`, `GITHUB_TOKEN` | GitHub repository operations and PR management |

### Model Provider Secrets

| Environment Variable | Purpose |
|---|---|
| `COMPATIBLE_URL` | OpenAI-compatible API base URL |
| `COMPATIBLE_MODEL` | Default model name for OpenAI-compatible provider |
| `BLABLADOR_API_KEY` | Model API key stored securely outside presets in `API_KEY_OTHER` |

### Key Distinctions

- `HF_TOKEN` (Hugging Face token) is **NOT** the LLM model API key.
- `HF_TOKEN` is **NOT** the Spynel API key (`SPYNEL_AGENT_ZERO_API_KEY`).
- `GITHUB_PAT` is **NOT** the Hugging Face token.

## 4. Deployed SHA Identity

Every OpenOperator deployment exposes its full source SHA via:

- `GET /health` -> `{"status": "ok", "sha": "<full-sha>"}`
- `/openoperator-build.json` -> `{"source_sha": "<full-sha>"}`

Acceptance smoke tests verify that `GET /health` returns a matching commit SHA before passing.
