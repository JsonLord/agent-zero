# Internal Comms Skill

## Functionality

The `internal-comms` skill is designed to assist in writing various types of internal communications, such as status reports, newsletters, and project updates. It provides a set of guidelines and templates to ensure that the communications are clear, consistent, and follow a company-approved format.

## Workflow

The workflow for this skill is straightforward:

1.  **Identify the Communication Type:** The agent first identifies the type of communication being requested (e.g., a 3P update, a company newsletter).

2.  **Load the Appropriate Guideline:** Based on the communication type, the agent loads a specific guideline file from the `examples/` directory. These files provide instructions on formatting, tone, and content.

3.  **Follow the Instructions:** The agent then follows the instructions in the guideline file to generate the communication.

## Authentication

The `internal-comms` skill does not have any direct authentication requirements. It is a writing-focused skill that provides templates and guidelines for generating text. It does not interact with any external services that require API keys or tokens. However, the content of the communications may be intended for platforms (e.g., an internal company blog or email system) that do require authentication.
