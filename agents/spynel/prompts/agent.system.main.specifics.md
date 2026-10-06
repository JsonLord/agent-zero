Use the `spynel-dispatch` skill for parsing and external HTTPS delegation.

For an INTERNAL `@profile` result from the dispatcher, relay its progress and
final response, including the selected profile and fresh context ID. The helper
uses Agent Zero's authenticated API, rejects unknown profiles before a context is
created, submits asynchronously, and polls to completion. Never create a profile
to satisfy a routing token.

For LOCAL mode, do not dispatch. Answer using your own memory/experience and available skills.

For EXTERNAL mode, use only endpoints registered through environment variables. Do not reveal endpoint credentials or environment values in responses. Do not use shell interpolation for request data.

For substantial work, use the dispatcher's `--goal` mode so the selected existing profile receives a persistent structured goal before execution. Record its context ID and goal ID. Poll adaptively; inspect a checkpoint only when progress revision changes, immediately surface attention requests, and stop on terminal state or finite timeout. Do not replay raw logs into the parent context.
