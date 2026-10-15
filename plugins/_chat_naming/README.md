# Chat Naming

Chat Naming adds a standard sidebar action for manually renaming chats and tasks. Its modal can ask the chat's configured Utility Model to suggest a concise name from recent user messages.

Automatic naming is configured per project and agent profile. It runs after the response, so its Utility Model call never delays the Main Model. It can name an unnamed chat once from its first user message, or refresh the name after every user message using recent user-only context.

Use `/rename New Chat Name` to rename the current chat directly, or `/rename auto` to generate and save a name with its configured Utility Model.

Automatic naming retains one background task per chat. Once mode can finish
while later messages arrive; always mode supersedes older requests. Manual
renames and deleted contexts reject late updates. The scoped setting
`automatic_naming_timeout_seconds` defaults to 45 and is clamped to 1–300 seconds.
This bounds the entire provider operation including any provider retries, without
changing global Utility Model settings. Failure preserves the title and allows
manual retry. The browser's 60,000ms rename-modal timeout is independent.
