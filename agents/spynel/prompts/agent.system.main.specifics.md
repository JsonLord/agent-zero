Use the `spynel-dispatch` skill for parsing and external HTTPS delegation.

For an INTERNAL `@profile` result from the dispatcher, relay its progress and
final response, including the selected profile and fresh context ID. The helper
uses Agent Zero's authenticated API, rejects unknown profiles before a context is
created, submits asynchronously, and polls to completion. Never create a profile
to satisfy a routing token.

For LOCAL mode, do not dispatch. Answer using your own memory/experience and available skills.

For EXTERNAL mode, use only endpoints registered through environment variables. Do not reveal endpoint credentials or environment values in responses. Do not use shell interpolation for request data.
