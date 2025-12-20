# Web Artifacts Builder Skill

## Functionality

The `web-artifacts-builder` skill is a suite of tools for creating complex, multi-component HTML artifacts using a modern frontend stack. It is designed for building artifacts that require state management, routing, or the use of a component library, and is not intended for simple, single-file HTML/JSX artifacts.

The stack used by this skill includes:

*   React 18
*   TypeScript
*   Vite
*   Parcel (for bundling)
*   Tailwind CSS
*   shadcn/ui

## Workflow

The workflow for this skill is as follows:

1.  **Initialize Project:** The agent uses the `scripts/init-artifact.sh` script to create a new, fully configured React project.

2.  **Develop Artifact:** The agent then develops the artifact by editing the generated code.

3.  **Bundle to Single HTML File:** Once development is complete, the agent uses the `scripts/bundle-artifact.sh` script to bundle the entire application into a single, self-contained HTML file.

4.  **Share Artifact:** The bundled HTML file can then be shared with the user.

5.  **Testing (Optional):** The artifact can be tested using other tools, such as Playwright.

## Authentication

The `web-artifacts-builder` skill does not have any direct authentication requirements. It is a developer-focused skill that provides a toolchain for building frontend artifacts. The tools it uses are all local and do not require API keys or tokens. However, the resulting artifact may itself need to interact with authenticated APIs.
