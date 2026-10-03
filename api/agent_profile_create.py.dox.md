# agent_profile_create.py DOX

## Purpose

- Create explicitly requested user-owned agent profiles through the administrative API.

## Ownership

- `agent_profile_create.py` validates profile metadata and persists it through `helpers.subagents`.

## Local Contracts

- Uses normal authenticated, CSRF-protected `ApiHandler` defaults.
- Accepts only a single safe profile name and flat prompt filenames; paths, reserved names, and replacements are rejected.
- Writes only beneath `usr/agents/` and never participates in Spynel routing.

## Work Guidance

- Preserve existing profile discovery and selection behavior.

## Verification

- Run `pytest tests/test_spynel.py`.

## Child DOX Index

No child DOX files.
