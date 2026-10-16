Use the tracked bundled `spynel-dispatch` skill from the application root for explicit routes, deterministic natural-language routes and validated interpretation of ordinary tasks. No extra routing inference request is needed.

For clear natural requests, pass the entire original message unchanged to the dispatcher. For an ordinary instruction that you interpret as specialist work, propose the existing profile with `--profile <registered-id>` (or a configured SDK with `--sdk`) and an existing canonical workspace/alias with `--workspace` when relevant. Explicit user tokens always win. These options cannot bypass registry validation, unknown/ambiguous target handling or file existence checks.

Use `python scripts/spynel_resolver.py --resolve-only '<original message>'` for read-only validation, or `--profile <registered-id> --workspace <existing-path>` with the same original message for a proposed selection. Never claim execution from a resolver result alone. Use the dispatcher to actually submit and poll the task.

For an INTERNAL `@profile` result from the dispatcher, relay its progress and
final response, including the selected profile and fresh context ID. The helper
uses Agent Zero's authenticated API, rejects unknown profiles before a context is
created, submits asynchronously, and polls to completion. Never create a profile
to satisfy a routing token.

For LOCAL mode, inspect the validation state. `abstain`, invalid paths and ambiguous targets require clarification; do not invoke a different tool to bypass that result. For an ordinary validated local instruction, answer using your existing memory/experience and skills. Unknown SDKs fail explicitly; never silently substitute a paid or unregistered service.

For EXTERNAL mode, use only endpoints registered through environment variables. Do not reveal endpoint credentials or environment values in responses. Do not use shell interpolation for request data.

For substantial work, use the dispatcher's `--goal` mode so the selected existing profile receives a persistent structured goal before execution. Record its context ID and goal ID. Poll adaptively; inspect a checkpoint only when progress revision changes, immediately surface attention requests, and stop on terminal state or finite timeout. Do not replay raw logs into the parent context.
