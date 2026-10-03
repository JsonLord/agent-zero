# Spynel Hugging Face Deployment and Integration Contract

## Scope

This document is the source of truth for the Spynel deployment branch. Changes
must remain modular and minimize invasive changes to Agent Zero core behavior.

## Hugging Face Docker Space

- The root Docker image must run Agent Zero as a non-root UID/GID 1000 process.
- The WebUI must listen on `0.0.0.0:7860`, and port 7860 must be the only
  required published port.
- Startup must not require `chpasswd`, SSH, cron, supervisor, sudo, privileged
  Docker flags, or another root-only service.
- Agent Zero application files must be readable by UID 1000. Runtime state and
  Hugging Face, XDG, and Matplotlib cache directories must be writable by UID
  1000.
- Kokoro, spaCy, their models, and other dependencies must be installed in a
  writable image-build layer. Runtime dependency installation must not be used
  to hide missing build dependencies or write into immutable image layers.
- Space startup errors must be fixed at their cause rather than suppressed.

## Administrative Profile Creation

- Provide an authenticated, CSRF-protected API for explicitly creating profiles
  under `usr/agents/` through existing profile persistence helpers.
- Validate profile names and prompt filenames, reject traversal/nested paths,
  reserved profiles, and duplicates, and preserve existing profile selection.
- Routing syntax must never invoke profile creation. An unknown routed profile
  must fail explicitly without creating a context or profile directory.

## Spynel Profile and Routing

Ship a bundled `spynel` Agent Zero profile with this routing grammar:

- `@profile`: route to an agent profile.
- `/sdk`: route to an SDK gateway.
- `@profile /sdk`: send profile metadata through the selected SDK gateway.
- No routing tokens: Spynel handles the request locally.

External routing contracts:

- `/sdk` resolves only from `SPYNEL_SDK_<SDK>_URL`.
- A registered `@profile` resolves only from `SPYNEL_AGENT_<PROFILE>_URL`.
- External destinations must be credential-free HTTPS URLs registered through
  environment variables; user text must never supply or override a destination.
- Dispatch uses shell-free curl argv execution, bounded connect/overall
  timeouts, terminate/kill cleanup, structured polling, progress states, and
  useful failure information.

Internal routing contracts:

- An unregistered `@profile` may select only an existing Agent Zero profile.
- Delegation uses configurable same-container loopback transport, preferably
  `SPYNEL_AGENT_ZERO_URL=http://127.0.0.1:7860`, authenticated with
  `SPYNEL_AGENT_ZERO_API_KEY`. HTTPS remains mandatory for non-loopback URLs.
- The Hugging Face entrypoint must configure Agent Zero's existing API-key
  verifier from `SPYNEL_AGENT_ZERO_API_KEY` without printing the secret.
- Delegation creates a fresh context, selects the requested profile, submits the
  stripped task asynchronously, polls with meaningful progression, and returns
  the result.
- Unknown profiles fail before context creation and are never implicitly
  created.

## Paperclip Skill

- Ship a Spynel-native Paperclip board-manager skill targeting
  `https://leon4gr45-paperclip-founder.hf.space` by default.
- Configuration uses `PAPERCLIP_BASE_URL` and optional
  `PAPERCLIP_API_TOKEN`.
- The helper permits credential-free HTTPS base URLs and confined `/api/*`
  paths, bounds timeouts, avoids shell interpolation, does not leak tokens, and
  preserves useful 401/403/404 response behavior.
- Live validation must use read-only requests unless disposable authenticated
  test data is explicitly available.

## Colab Lifecycle CLI

Provide a CLI that starts Agent Zero in the background, checks `/api/health`,
and stops the process group. It must handle stale PID files, graceful shutdown,
and bounded forced termination fallback.

## Required Validation

- Clean-build the actual root Docker image and run it without development bind
  mounts or privileged flags as UID/GID 1000.
- Verify `/api/health`, the UI root, authenticated API access, Spynel profile and
  profile-scoped skill discovery, administrative profile auth/CSRF, writable
  state/cache paths, and clean startup logs.
- Run internal Spynel delegation, explicit unknown-profile safety, controlled
  immediate/async HTTPS external fixtures, read-only live Paperclip checks,
  disposable profile creation, and the Colab lifecycle.
- Install the real framework dependencies and run the complete pytest suite plus
  focused Spynel, Python compilation, shell syntax, and diff checks.
- Do not claim Hugging Face readiness unless the image builds and the resulting
  non-root container successfully serves `/api/health`.
