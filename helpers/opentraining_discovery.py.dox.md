# OpenTraining discovery

`public_url()` validates an HTTP(S) origin, rejecting credentials, query strings,
fragments, paths, malformed ports and HF loopback identity. Explicit A0_PUBLIC_URL
wins, followed by HF SPACE_HOST, SPACE_ID, and dedicated HF fallback. Local callers
may use the library's local default. No credentials are read or emitted.

`discovery_routes()` supplies public Starlette endpoints for health, human integration
docs, the static FastA2A 0.5 wire contract and existing API docs. Health reads only the
optional build manifest's validated source SHA. It never generates an identity or
initializes model/agent state. A2A itself remains authenticated. Task state is volatile;
this contract does not qualify controller mutations or durable remote observation.

Verify through real ASGI tests in tests/test_opentraining_a2a.py.
