# Shared A2A discovery

`bootstrap_links`, `a2a_contract`, and `integration_docs` provide identical public,
credential-free discovery metadata/content to ASGI and the existing Flask/WSGI
fallback. They read only the tracked Markdown, without importing models, resolving
credentials, touching campaign state or performing network requests. Missing Markdown
is handled by callers with a bounded 404. The contract advertises read-only Argus
operations only; it does not enable A2A or grant controller authority.

Verify both actual ASGI and Flask paths in tests/test_a2a_boundary.py.
