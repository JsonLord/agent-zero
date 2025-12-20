# Algorithmic Art Skill

## Functionality

The `algorithmic-art` skill is designed to create generative art using the p5.js library. It follows a two-step process:

1.  **Algorithmic Philosophy Creation:** The agent first generates a document (.md file) that defines an "algorithmic philosophy." This philosophy is a creative and conceptual framework for the generative art, describing the aesthetic movement, its principles, and how it manifests through computational processes.

2.  **P5.js Implementation:** The agent then uses this philosophy to create an interactive, self-contained HTML artifact. This artifact includes a p5.js sketch that brings the philosophy to life, allowing for real-time exploration of the generative art through adjustable parameters and seeded randomness.

## Workflow

1.  **Philosophy Creation:**
    *   The agent creates an algorithmic philosophy, which includes a name for the movement and a detailed articulation of its principles.
    *   This philosophy is saved as a markdown file.

2.  **Implementation:**
    *   The agent uses a provided template (`templates/viewer.html`) as the foundation for the HTML artifact.
    *   It implements a p5.js algorithm that expresses the philosophy, using seeded randomness for reproducibility.
    *   It defines a set of parameters that allow for real-time control of the generative art.
    *   The final output is a single, self-contained HTML file that can be opened in any browser.

## Authentication

The `algorithmic-art` skill does not have any direct authentication requirements. It uses the p5.js library from a CDN and does not interact with any external services that require API keys or tokens.
