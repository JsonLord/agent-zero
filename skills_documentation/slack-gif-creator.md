# Slack GIF Creator Skill

## Functionality

The `slack-gif-creator` skill is a toolkit for creating animated GIFs that are optimized for use in Slack. It provides a set of utilities and guidelines for generating GIFs that meet Slack's requirements for dimensions, frame rate, and file size.

## Workflow

The core workflow for this skill involves:

1.  **Creating a GIFBuilder:** The agent initializes a `GIFBuilder` object with the desired dimensions and frame rate.

2.  **Generating Frames:** The agent then generates a series of frames for the animation. This can be done by drawing from scratch using the Python Imaging Library (PIL) or by using user-uploaded images.

3.  **Saving the GIF:** Finally, the agent saves the frames as a GIF, with options for optimizing the file size for Slack.

The skill also provides a set of helper utilities, including:

*   **Validators:** To check if a GIF meets Slack's requirements.
*   **Easing Functions:** To create smooth and natural-looking animations.
*   **Frame Helpers:** For common tasks like creating blank frames and drawing simple shapes.

## Authentication

The `slack-gif-creator` skill does not have any direct authentication requirements. It is a creative and technical skill that focuses on generating animated GIFs and does not interact with any external services that require API keys or tokens. However, the skill does have a number of dependencies that must be installed in the environment for it to function correctly, including `pillow`, `imageio`, and `numpy`.
