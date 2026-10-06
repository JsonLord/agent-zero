# api_poll.py DOX

## Purpose

- Expose bounded incremental status for API-created asynchronous chats.

## Ownership

- `api_poll.py` owns the API-key-protected polling response.

## Local Contracts

- Requires the existing Agent Zero API key; browser authentication and CSRF are not used.
- Never creates a context and returns 404 for unknown context identifiers.
- Returns compact semantic goal state, milestone, progress revision, attention signal, and the final result. Incremental raw logs are returned only when `include_logs: true` is requested.

## Work Guidance

- Keep this endpoint compatible with `api/api_message.py` asynchronous submissions.

## Verification

- Run the Spynel and API-message tests.

## Child DOX Index

No child DOX files.
