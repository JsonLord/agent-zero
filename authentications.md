# Required Authentications for Sub-Agents

This document lists the required authentication tokens and API keys for the various sub-agents to function effectively.

## `git-agent`

-   **Service:** GitHub
-   **Authentication:** GitHub Personal Access Token (PAT)
-   **Scope:** The token must have the `repo` scope to allow for creating branches, committing changes, and creating pull requests.
-   **Setup:** The token should be provided to the `git-agent` when it runs `gh auth login --with-token <token>`.

## `huggingface` agent

-   **Service:** Hugging Face Hub
-   **Authentication:** Hugging Face Access Token
-   **Scope:** The token must have `write` permissions to allow for creating repositories and uploading files.
-   **Setup:** The token should be provided to the `huggingface` agent when it runs `hf login <token>`.

## `jules` agent

-   **Service:** Jules API
-   **Authentication:** Jules API Key
-   **Setup:** The API key should be provided to the `jules` agent via the `JULES_API_KEY` environment variable or directly in API calls using the `X-Goog-Api-Key` header.

## Other Skills

The following skills, which are grouped under the `designer`, `document_automator`, and `developer` agents, do not have explicit authentication requirements themselves. However, they may be used to interact with services that do require authentication.

-   `algorithmic-art`
-   `brand-guidelines`
-   `canvas-design`
-   `doc-coauthoring` (may use authenticated integrations if available in the environment)
-   `docx`
-   `frontend-design`
-   `internal-comms`
-   `mcp-builder`
-   `pdf`
-   `pptx`
-   `skill-creator`
-   `slack-gif-creator`
-   `theme-factory`
-   `web-artifacts-builder`
-   `webapp-testing`
-   `xlsx`
