# PPTX Skill

## Functionality

The `pptx` skill provides a comprehensive toolkit for creating, editing, and analyzing .pptx files. It supports a wide range of operations, including:

*   **Reading and Analyzing:** Extracting text content and accessing raw XML for more complex analysis of comments, speaker notes, and design elements.
*   **Creating New Presentations:** Generating new PowerPoint presentations from scratch or by using an existing template.
*   **Editing Existing Presentations:** Modifying existing presentations by directly editing the underlying OOXML.

## Workflow

The skill provides several workflows for different tasks:

*   **Reading/Analyzing:**
    *   For simple text extraction, the agent uses `markitdown` to convert the .pptx file to markdown.
    *   For more complex analysis, the agent unpacks the .pptx file to access the raw OOXML.

*   **Creating New Presentations (from scratch):**
    *   The agent uses an `html2pptx` workflow to convert HTML slides into a PowerPoint presentation.
    *   This workflow includes a strong emphasis on design principles, such as color palette selection and layout.

*   **Creating New Presentations (from a template):**
    *   The agent analyzes an existing template, duplicates and reorders the slides as needed, and then replaces the placeholder content with new text.

*   **Editing Existing Presentations:**
    *   The agent unpacks the .pptx file and directly edits the OOXML to make changes.

## Authentication

The `pptx` skill does not have any direct authentication requirements. The tools it uses (`markitdown`, `pptxgenjs`, and Python libraries for OOXML) are all local and do not require API keys or tokens. However, the skill does have a number of dependencies that must be installed in the environment for it to function correctly, including `markitdown`, `pptxgenjs`, `playwright`, `sharp`, `libreoffice`, and `poppler-utils`.
