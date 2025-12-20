# DOCX Skill

## Functionality

The `docx` skill provides a comprehensive toolkit for creating, editing, and analyzing .docx files. It supports a wide range of operations, including:

*   **Reading and Analyzing:** Extracting text content and accessing raw XML for more complex analysis of comments, formatting, and metadata.
*   **Creating New Documents:** Generating new Word documents from scratch using JavaScript/TypeScript with the `docx-js` library.
*   **Editing Existing Documents:** Modifying existing documents, with a special "redlining" workflow for tracking changes, which is recommended for collaborative and professional contexts.

## Workflow

The skill provides a decision tree to guide the agent in choosing the appropriate workflow based on the task:

*   **Reading/Analyzing:**
    *   For simple text extraction, the agent uses `pandoc` to convert the .docx file to markdown.
    *   For more complex analysis, the agent unpacks the .docx file to access the raw OOXML.

*   **Creating New Documents:**
    *   The agent uses the `docx-js` library to create a new document with JavaScript/TypeScript.
    *   The final document is exported as a .docx file.

*   **Editing Existing Documents:**
    *   For simple edits, the agent can use a Python library to manipulate the OOXML directly.
    *   For more formal or collaborative editing, the agent uses a "redlining" workflow that involves creating tracked changes in the document.

## Authentication

The `docx` skill does not have any direct authentication requirements. The tools it uses (`pandoc`, `docx-js`, and Python libraries for OOXML) are all local and do not require API keys or tokens. However, the skill does have a number of dependencies that must be installed in the environment for it to function correctly, including `pandoc`, `npm`, `libreoffice`, and `poppler-utils`.
