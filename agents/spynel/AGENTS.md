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
- Use structured goal delegation for multi-stage outcomes, idempotently retain accepted context/goal IDs, and poll semantic progress revisions with bounded adaptive backoff.

## Work Guidance

- Keep routing helpers independently testable and return structured state events.

## Verification

- Run `pytest tests/test_spynel.py`.

## Child DOX Index

No child DOX files.

- `scripts/spynel_resolver.py` is the shared read-only deterministic recognizer;
  discover active profiles through `subagents.get_available_agents_dict` and
  external routes only through credential-free HTTPS environment registrations.
- Natural requests preserve original text; workspace paths must already exist
  beneath `/a0/usr/workdir` after symlink resolution. Ambiguity abstains.
- The optional HTTPS classifier is disabled by default and may select only an
  exact validated candidate or abstain; it never discovers or dispatches targets.
