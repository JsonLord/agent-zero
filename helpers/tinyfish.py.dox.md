# Tinyfish REST fallback

`configured()` checks only the presence of `TINYFISH_API_KEY`; its value is never
logged or persisted. `search(query, timeout=15)` uses GET
`https://api.search.tinyfish.ai?query=...`, returning normalized title/URL/snippet
records. `fetch(url, timeout=30, max_bytes=...)` uses POST
`https://api.fetch.tinyfish.ai` with `{"urls":[url],"format":"markdown"}` and returns
(final HTTPS URL, UTF-8 Markdown bytes). Authentication is `X-API-Key`.

Both services use verified TLS, the inherited proxy, bounded connection/total
budgets and response sizes, no redirects and no automatic provider retries.
Public-URL validation applies before fetch and to its final URL. Private or
credentialed targets and cancellation never authorize a fallback. Missing keys
and provider failures use safe `TinyfishError` codes without response bodies or
headers. Empty search results succeed; failed or empty page extractions do not.

Contract sources: Tinyfish's official `tinyfish-web-agent-integrations` Hermes
REST client and `tinyfish-cookbook/skills/tinyskill/SKILL.md`. Run
`tests/test_tinyfish_fallback.py`, `tests/test_search_reliability.py` and the
existing document-query security tests. Live access requires the operator's key;
unit tests use controlled responses and need no real credentials.
