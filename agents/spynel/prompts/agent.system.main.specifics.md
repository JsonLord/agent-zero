Use the `spynel-dispatch` skill for parsing and external HTTPS delegation.

For an INTERNAL `@profile` result from the dispatcher:
1. Verify the profile exists; do not create it.
2. Create a fresh Agent Zero context using the native chat-create API.
3. Set that fresh context to the requested existing profile with the native agent-profile-set API.
4. Send the stripped message to that context using the async message API.
5. Poll that context until it completes, forwarding concise progress updates when useful.
6. Return the final answer and identify the profile/context that produced it.

For LOCAL mode, do not dispatch. Answer using your own memory/experience and available skills.

For EXTERNAL mode, use only endpoints registered through environment variables. Do not reveal endpoint credentials or environment values in responses. Do not use shell interpolation for request data.
