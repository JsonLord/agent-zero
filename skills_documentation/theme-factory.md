# Theme Factory Skill

## Functionality

The `theme-factory` skill is a toolkit for styling artifacts, such as presentations, documents, and HTML landing pages, with a consistent and professional theme. It provides a collection of 10 pre-set themes, each with its own color palette and font pairings, and also allows for the creation of custom themes.

## Workflow

The workflow for this skill is as follows:

1.  **Theme Selection:**
    *   The agent can display a `theme-showcase.pdf` file to the user to visually present the available themes.
    *   The user then selects a theme to apply to their artifact.

2.  **Theme Application:**
    *   Once a theme is selected, the agent reads the corresponding theme file from the `themes/` directory.
    *   It then applies the specified colors and fonts to the artifact, ensuring a consistent and professional look.

3.  **Custom Theme Creation:**
    *   If none of the pre-set themes are suitable, the agent can create a custom theme based on the user's input.
    *   The agent generates a new theme with a name, color palette, and font pairings, and then applies it to the artifact.

## Authentication

The `theme-factory` skill does not have any direct authentication requirements. It is a creative skill that focuses on styling artifacts and does not interact with any external services that require API keys or tokens. However, the skill is designed to be used in conjunction with other tools (e.g., for creating presentations or HTML pages), which may have their own dependencies or requirements.
