# Doc Co-Authoring Skill

## Functionality

The `doc-coauthoring` skill provides a structured, collaborative workflow for creating documents such as proposals, technical specs, and decision docs. It guides the user through a three-stage process designed to ensure the final document is clear, comprehensive, and effective for its intended audience.

## Workflow

The workflow is divided into three main stages:

1.  **Context Gathering:** The agent actively gathers all relevant information from the user, including the document's purpose, audience, and any existing templates or related materials. This stage may involve the use of integrations to access shared documents or team channels.

2.  **Refinement & Structure:** The document is built section by section through an iterative process of brainstorming, curation, and drafting. The agent works with the user to define the document's structure and then collaboratively refines each section until it is complete.

3.  **Reader Testing:** The final document is tested to ensure it is clear and understandable to a reader who does not have the context of the co-authoring process. This is done by using a "fresh" agent instance (a sub-agent) to answer questions based on the document, identifying any ambiguities or gaps in the content.

## Authentication

The `doc-coauthoring` skill does not have any direct authentication requirements. However, it is designed to be used with integrations that may require authentication to access external services such as:

*   **Slack**
*   **Microsoft Teams**
*   **Google Drive**
*   **SharePoint**
*   **Other MCP servers**

If these integrations are available and the user wants to use them to provide context, the appropriate authentication must be in place for the agent to access these services.
