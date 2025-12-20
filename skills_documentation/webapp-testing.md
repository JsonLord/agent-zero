# WebApp Testing Skill

## Functionality

The `webapp-testing` skill is a toolkit for interacting with and testing local web applications using Playwright. It provides a set of tools and best practices for:

*   **Verifying frontend functionality:** Writing scripts to automate interactions with a web application and verify that it behaves as expected.
*   **Debugging UI behavior:** Capturing screenshots and inspecting the DOM to diagnose and fix issues.
*   **Capturing browser logs:** Viewing console logs to help with debugging.

## Workflow

The skill provides a decision tree to guide the agent in choosing the appropriate testing approach:

*   **Static HTML:** For static HTML files, the agent can read the file directly to identify selectors and then use those selectors in a Playwright script.
*   **Dynamic Webapp:** For dynamic web applications, the agent uses a "reconnaissance-then-action" pattern:
    1.  It first navigates to the page and waits for it to be fully loaded.
    2.  It then takes a screenshot or inspects the DOM to identify the necessary selectors.
    3.  Finally, it uses those selectors to execute actions and assertions.

The skill also includes a helper script, `scripts/with_server.py`, which can be used to manage the lifecycle of the web server during testing.

## Authentication

The `webapp-testing` skill does not have any direct authentication requirements. It is a developer-focused skill that provides a toolchain for testing web applications. The tools it uses are all local and do not require API keys or tokens. However, the web application being tested may itself require authentication, and the Playwright scripts may need to be written to handle the login process.
