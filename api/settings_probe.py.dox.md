# settings_probe.py DOX

## Purpose

- Provide an API-key-protected, secret-safe deployment acceptance surface.

## Contract

- `get` returns ordinary masked settings metadata through `convert_out`, numeric UID/GID where supported, and only the main model's non-secret provider/name/base fields.
- `set_time_format` is the only mutation and accepts only `12h` or `24h`, enabling a harmless reversible save/reload smoke.
- The route does not weaken browser authentication or CSRF and never returns the effective API token or provider secrets.

## Verification

- Run API-token authority and HF smoke tests.
