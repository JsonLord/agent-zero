# Spynel Profile DOX

## Purpose

- Own the bundled Spynel routing profile and its native dispatch and Paperclip skills.

## Ownership

- `agent.yaml` and `prompts/` define routing behavior.
- `skills/spynel-dispatch/` owns safe internal/external delegation.
- `skills/paperclip-board-manager/` owns the Paperclip API workflow.

## Local Contracts

- Routing tokens never create profiles; unregistered names must already exist or fail.
- External endpoints are environment-registered, credential-free HTTPS URLs.
- Do not expose API tokens or pass user content through a shell.

## Work Guidance

- Keep routing helpers independently testable and return structured state events.

## Verification

- Run `pytest tests/test_spynel.py`.

## Child DOX Index

No child DOX files.
