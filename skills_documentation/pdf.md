# PDF Skill

## Functionality

The `pdf` skill provides a comprehensive toolkit for processing and manipulating PDF documents. It supports a wide range of operations, including:

*   **Reading and Extracting:** Extracting text, tables, and metadata from PDF files.
*   **Creating and Modifying:** Creating new PDFs from scratch, as well as merging, splitting, rotating, and watermarking existing documents.
*   **Form Handling:** Filling out PDF forms.
*   **OCR:** Extracting text from scanned PDFs using optical character recognition.

## Workflow

The skill provides a variety of tools and libraries to accomplish these tasks, with a focus on Python libraries and command-line utilities:

*   **Python Libraries:**
    *   `pypdf`: For basic operations like merging, splitting, and rotating.
    *   `pdfplumber`: For more advanced text and table extraction.
    *   `reportlab`: for creating new PDF documents.
*   **Command-Line Tools:**
    *   `pdftotext`: For extracting text from PDFs.
    *   `qpdf`: For merging, splitting, and rotating PDFs.
    *   `pdftk`: An alternative for merging, splitting, and rotating.

The skill also provides guidance on common tasks such as OCR, adding watermarks, and password protection.

## Authentication

The `pdf` skill does not have any direct authentication requirements. The tools and libraries it uses are all local and do not require API keys or tokens. However, the skill does have a number of dependencies that must be installed in the environment for it to function correctly, including `pypdf`, `pdfplumber`, `reportlab`, `pytesseract`, `pdf2image`, and `poppler-utils`.
