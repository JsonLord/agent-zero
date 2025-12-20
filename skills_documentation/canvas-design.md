# Canvas Design Skill

## Functionality

The `canvas-design` skill is designed to create beautiful and visually rich static art, such as posters and other design pieces, in .png and .pdf formats. It follows a two-step process:

1.  **Design Philosophy Creation:** The agent first generates a document (.md file) that defines a "visual philosophy." This philosophy is a creative and conceptual framework for the design, describing the aesthetic movement, its principles, and how it manifests through form, space, color, and composition.

2.  **Canvas Creation:** The agent then uses this philosophy to create a visual artifact on a canvas. This artifact is a high-quality, design-forward piece that embodies the principles of the philosophy, with minimal text and a strong emphasis on visual communication.

## Workflow

1.  **Philosophy Creation:**
    *   The agent creates a visual philosophy, which includes a name for the movement and a detailed articulation of its principles.
    *   This philosophy is saved as a markdown file.

2.  **Canvas Creation:**
    *   The agent uses the design philosophy as a guide to create a visual piece on a canvas.
    *   It uses a variety of design elements, such as color, shape, and typography, to express the philosophy.
    *   The final output is a single, downloadable .pdf or .png file, alongside the design philosophy used as a .md file.

## Authentication

The `canvas-design` skill does not have any direct authentication requirements. It is a creative skill that focuses on generating visual content and does not interact with any external services that require API keys or tokens. However, it may use external fonts from the `./canvas-fonts` directory, which should be available in the environment.
