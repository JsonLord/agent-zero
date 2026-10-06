# hf_space_defaults.py DOX

## Purpose

- Apply non-empty Hugging Face Space compatible-provider environment defaults at startup.

## Ownership

- `apply_hf_space_defaults()` maps `COMPATIBLE_URL` and `COMPATIBLE_MODEL` to the Default preset's main `chat` slot and maps `BLABLADOR_API_KEY` only to `API_KEY_OTHER` secret storage.

## Runtime Contracts

- Provider ID `other` is Agent Zero's OpenAI-compatible provider.
- Non-empty environment values are authoritative; absent values never erase persisted values.
- Utility and embedding slots are not modified.
- Secret values never enter model preset files or logs.
- When non-empty authoritative values cannot be persisted, startup fails rather than silently serving a misconfigured model.

## Verification

- Run `pytest tests/test_hf_space_defaults.py`.
