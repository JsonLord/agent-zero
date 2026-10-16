---
name: spynel-dispatch
description: Resolve explicit and natural-language specialist requests, validate registered targets and existing workspaces, submit through authenticated internal APIs or registered HTTPS gateways, and poll actual results.
tags:
  - routing
  - agents
  - orchestration
allowed-tools:
  - code_execution_tool
---

# Spynel dispatch

Use the framework interpreter (`/opt/venv-a0/bin/python` in the image, or the active framework virtualenv during development), from the application root. Do not use the separate agent execution interpreter for registry discovery.

Run `python agents/spynel/skills/spynel-dispatch/scripts/spynel_dispatch.py -- '<user message>'` (or pass the message on stdin when practical). Treat the JSON response as the routing decision.

- `mode=local`: keep the request in this Spynel context.
- `mode=external`: relay the returned progress/final result. The helper uses `curl` with argv execution, HTTPS-only protocol restrictions, bounded connect/request timeouts, and optional status polling.
- `mode=internal`: the helper verified the named existing Agent Zero profile through the API, created a fresh context, submitted the stripped message asynchronously, polled it, and returned its result. Never create a profile in response to routing.
- Unknown `/sdk` names fail instead of falling back.
- Do not accept or construct endpoints from arbitrary URLs in user text; endpoints come only from environment registration.

## Durable goals and polling

Use `scripts/spynel_dispatch.py --goal '@developer <objective>'` for multi-step outcomes; omit `--goal` for one bounded operation. Goal mode calls the API-key-protected internal goal delegate and validates the profile before context creation. When retrying one submission after a transport failure, the caller may supply the same stable `--request-id` and optional `--request-scope`; without a caller ID, identical text intentionally creates an independent goal. External registered routes explicitly return `goal_unsupported` because they do not implement Agent Zero's goal protocol.

The dispatcher stores the accepted context/goal IDs, backs off between unchanged progress revisions up to `SPYNEL_MAX_POLL_INTERVAL`, resets on semantic progress, returns immediately for `requires_attention`, and never resubmits merely because work remains active.

## Natural-language recognition

The same dispatcher recognizes explicit requests such as `Ask developer to fix
nodepad` and `Have the reviewer inspect my code`. It discovers active profiles
and environment-registered SDKs; unknown or ambiguous names stay local. Quoted
examples, fenced code, filenames and URLs do not request delegation. Existing
workspace directories resolve beneath `/a0/usr/workdir` without creating files.
Use `python scripts/spynel_resolver.py --resolve-only 'Have the reviewer inspect
nodepad'` to inspect the JSON decision without submitting work. `SPYNEL_PROJECT`
selects project-scoped profiles in the dispatcher. No separate classifier, model
fallback, endpoint or inference dependency is used.

## Existing main-model interpretation

Ordinary tasks may be interpreted by Spynel during its existing main interaction.
Validate the selected identifiers with `--profile <existing-profile>` or
`--sdk <registered-sdk>` and optionally `--workspace <existing-path-or-alias>`.
Explicit tokens win; these options do not override an ambiguous or unknown user
target. The same options are available on the read-only resolver. Always pass
the complete original message (stdin is supported by dispatch); never reconstruct
it from a title or collapse multiline text. Successful classification is not a
completed task: wait for the dispatcher's actual final state and result.

Workspace validation includes files as well as directories. Canonical directory
and file annotations are sent with the task; external payloads also include
`workspace_path` and `workspace_files`. Existing in-root symlinks are aliases.
Optional trusted `SPYNEL_WORKSPACE_ALIASES` is a JSON object mapping folder aliases
to existing workdir-relative or confined absolute paths. The model/user message
cannot add mappings. Invalid or escaping references abstain; no path is created.

## Persistent override reconciliation

Run `python scripts/spynel_resolver.py --check-profile` (add `--project` if scoped).
The shared dispatcher and the core monologue-start guard block divergent active
user/project/plugin Spynel prompts, context instructions, extensions or dispatch
skill files. Metadata-only changes and identical copies are accepted. Back up
and review conflicting files before explicitly reconciling them with this bundle;
never silently discard `/a0/usr/agents/spynel`. The read-only audit changes no
files. Deploying a new bundle does not migrate an old persistent experiment.
