# searxng.py DOX

## Purpose

- Own the `searxng.py` helper module.
- This module queries SearXNG search.
- Keep this file-level DOX profile synchronized with `searxng.py` because this directory is intentionally flat.

## Ownership

- `searxng.py` owns the runtime implementation.
- `searxng.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Top-level functions:
- `async search(query: str)`
- `async _search(query: str)`
- Notable constants/configuration names: `URL`.

## Runtime Contracts

- Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
- Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
- Observed side-effect areas: network calls, settings/state persistence.
- Imported dependency areas include: `aiohttp`, `helpers`.

## Key Concepts

- Important called helpers/classes observed in the source: `runtime.call_development_function`, `aiohttp.ClientSession`, `session.post`, `response.json`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Preserve public helper APIs used by core code and plugins unless every caller is updated.
- Keep path, auth, secret, persistence, network, and subprocess behavior explicit and bounded.
- Prefer adding cohesive helper functions here only when behavior is reused across modules.

## Verification

- Run targeted tests for changed helper behavior; run security regressions for auth, filesystem, WebSocket, tunnel, upload, or secret-handling helpers.
- No direct test reference was found by name search; choose the nearest behavioral test or perform a focused smoke check.

## Child DOX Index

No child DOX files.

## Reliability and configuration

`A0_SEARCH_BACKEND=auto` tries SearXNG then the already declared free
DuckDuckGo provider; `searxng` and `duckduckgo` select a single backend.
`A0_SEARXNG_URL` overrides the loopback endpoint. Each provider is bounded by
`A0_SEARCH_TIMEOUT_SECONDS` (default 15, range 1–60); HTTP connect has a 3s cap.
DuckDuckGo uses its HTML endpoint through verified `aiohttp` TLS and environment
proxy support. Its pinned DDGS client disables verification internally and is
not used. Cancellation propagates and closes HTTP sessions. Empty results are successful. Failures return
safe reason codes and empty results; provider response bodies and secrets are
never included. No paid backend is selected. Run `tests/test_search_reliability.py`.

When `TINYFISH_API_KEY` is present, Tinyfish Search is the immediate next provider
following a selected provider failure (auto order: SearXNG, Tinyfish, DuckDuckGo).
Explicit single-provider selections also gain this authorized fallback;
`A0_SEARCH_BACKEND=tinyfish` selects it directly. Missing keys preserve the
existing free-provider order. Healthy/empty results and cancellation do not
trigger fallback. No retry/backoff is inserted before Tinyfish.
