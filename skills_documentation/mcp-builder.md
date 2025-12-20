# MCP Builder Skill

## Functionality

The `mcp-builder` skill provides a comprehensive guide for creating high-quality MCP (Model Context Protocol) servers. These servers enable Large Language Models (LLMs) to interact with external services through a set of well-designed tools. The skill covers the entire development lifecycle, from research and planning to implementation, testing, and evaluation.

## Workflow

The workflow is divided into four main phases:

1.  **Deep Research and Planning:** This phase involves understanding modern MCP design principles, studying the MCP specification, and planning the implementation. It emphasizes the importance of clear tool naming, effective context management, and actionable error messages.

2.  **Implementation:** This phase covers the practical aspects of building the MCP server, including setting up the project structure, implementing core infrastructure, and creating the individual tools. The recommended stack is TypeScript with the MCP SDK.

3.  **Review and Test:** This phase focuses on ensuring the quality of the MCP server through code reviews and testing with the MCP Inspector.

4.  **Create Evaluations:** The final phase involves creating a set of evaluation questions to test the effectiveness of the MCP server in a realistic context.

## Authentication

The `mcp-builder` skill itself does not have any direct authentication requirements. However, a key part of the workflow is to **"Understand the API"** you are building the MCP server for. This includes identifying the authentication requirements of that API.

Therefore, while the `mcp-builder` skill doesn't require authentication, the MCP server it helps you build **will almost certainly require authentication** to interact with the target API. The skill guides you to implement this authentication in the "Core Infrastructure" section of your MCP server. The specific authentication method will depend on the API you are integrating with.
