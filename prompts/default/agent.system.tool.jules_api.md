### jules_api:
A tool for interacting with the Jules API. Use this tool to manage remote development sessions, interact with GitHub repositories, and automate tasks related to online code repositories.

**Arguments:**
* `endpoint` (string, required) - The API endpoint to call (e.g., "sources", "sessions").
* `method` (string, optional) - The HTTP method to use (e.g., "GET", "POST"). Defaults to "GET".
* `data` (string, optional) - The JSON data to send with the request.

For a full list of available endpoints and their parameters, see the documentation in `knowledge/jules_api_documentation.md`.
The `JULES_API_KEY` environment variable must be set to use this tool.
