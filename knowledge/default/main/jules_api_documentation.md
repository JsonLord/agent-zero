# Jules API Tool Documentation

The `jules_api` tool provides a convenient way to interact with the Jules API directly from your agent. It simplifies the process of making API calls by handling authentication and request formatting for you.

## Available Commands

The tool supports the following commands:

- `list_sources`: Lists all available sources.
- `create_session`: Creates a new session.
- `list_sessions`: Lists all sessions.
- `approve_plan`: Approves a plan for a session.
- `list_activities`: Lists all activities for a session.
- `send_message`: Sends a message to a session.

## Usage

To use the tool, you need to provide the `command` argument with the name of the command you want to execute. Some commands may require additional arguments.

### `list_sources`

This command lists all available sources.

**Arguments:**

- `command`: `list_sources`

**Example:**

```
jules_api(command="list_sources")
```

### `create_session`

This command creates a new session.

**Arguments:**

- `command`: `create_session`
- `data`: A JSON string containing the session data.

**Example:**

```
jules_api(command="create_session", data='{"prompt": "Create a boba app!", "sourceContext": {"source": "sources/github/bobalover/boba", "githubRepoContext": {"startingBranch": "main"}}, "automationMode": "AUTO_CREATE_PR", "title": "Boba App"}')
```

### `list_sessions`

This command lists all sessions.

**Arguments:**

- `command`: `list_sessions`
- `pageSize` (optional): The number of sessions to return. Defaults to 5.

**Example:**

```
jules_api(command="list_sessions", pageSize=10)
```

### `approve_plan`

This command approves a plan for a session.

**Arguments:**

- `command`: `approve_plan`
- `session_id`: The ID of the session.

**Example:**

```
jules_api(command="approve_plan", session_id="31415926535897932384")
```

### `list_activities`

This command lists all activities for a session.

**Arguments:**

- `command`: `list_activities`
- `session_id`: The ID of the session.
- `pageSize` (optional): The number of activities to return. Defaults to 30.

**Example:**

```
jules_api(command="list_activities", session_id="31415926535897932384", pageSize=50)
```

### `send_message`

This command sends a message to a session.

**Arguments:**

- `command`: `send_message`
- `session_id`: The ID of the session.
- `data`: A JSON string containing the message data.

**Example:**

```
jules_api(command="send_message", session_id="31415926535897932384", data='{"prompt": "Can you make the app corgi themed?"}')
```
