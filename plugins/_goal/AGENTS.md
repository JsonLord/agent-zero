# Goal Plugin DOX

## Purpose

- Own durable per-context execution goals, `/goal`, authenticated orchestration APIs, compact prompt injection, and the goal strip.

## Ownership

- `tools/goal.py` owns the structured state machine and atomic persistence under ignored `usr/plugins/_goal/goals/`.
- `api/goal.py` is browser session/CSRF protected; `api/delegate.py` is separately API-key protected for Spynel.
- `commands/`, prompts, extensions, and WebUI own interactive controls, compact injection, loop continuation, and display.

## Local Contracts

- Goal states are active, interrupted, pending, paused, blocked, completed, partially_verified, failed, and cancelled; legacy complete normalizes to completed. Final states cannot implicitly resume, and activation must correspond to a runnable worker.
- Goal definition and semantic progress revisions are distinct. Routine transport or shell operations do not increment progress.
- Completion evaluates structured criteria: only a non-empty all-PASS set with no unfinished children is completed; zero criteria or NOT_VERIFIED is partially_verified and FAIL is failed.
- Attention reasons use the bounded machine-readable vocabulary in `tools/goal.py`.
- Contexts have one current goal. Child goals have separate contexts, bounded hierarchy, sibling-scoped acyclic dependencies, and request/scoped idempotency keys.
- In-process mutations share a re-entrant lock so read-modify-write updates cannot overwrite each other. Atomic replacement protects file integrity; multi-process writers are outside the supported store boundary.
- The plugin startup migration reconciles persisted active goals. Missing workers become interrupted. Explicit resume may move non-operational work to a fresh context while preserving goal identity and evidence; operational recovery requires approval and never automatically replays side effects.
- Files survive process/container restarts only when the configured user directory is persistent; ephemeral Hugging Face storage is not durable across Space replacement.
- High autonomy never bypasses authentication, approval, secret, or external-write protections.
- Browser state uses existing state-push; Spynel uses compact adaptive polling fallback.

## Work Guidance

- Keep records compact, atomic, collision-resistant, and outside tracked source.
- Do not turn goals into a project manager; Paperclip remains the durable issue/project surface.

## Verification

- Run `pytest plugins/_goal/tests tests/test_spynel.py` and relevant API auth tests.

## Child DOX Index

No child DOX files.
