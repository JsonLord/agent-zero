# XLSX Skill

## Functionality

The `xlsx` skill provides a comprehensive toolkit for creating, editing, and analyzing spreadsheets in various formats, including .xlsx, .xlsm, .csv, and .tsv. It supports a wide range of operations, including:

*   **Data Analysis:** Reading and analyzing data from spreadsheets using the `pandas` library.
*   **Formula and Formatting:** Creating and editing spreadsheets with formulas and custom formatting using the `openpyxl` library.
*   **Formula Recalculation:** Recalculating all formulas in a spreadsheet to ensure that the values are up to date.

## Workflow

The skill provides a common workflow for working with Excel files:

1.  **Choose Tool:** The agent selects the appropriate tool for the task: `pandas` for data analysis or `openpyxl` for working with formulas and formatting.

2.  **Create/Load:** The agent creates a new workbook or loads an existing file.

3.  **Modify:** The agent adds or edits data, formulas, and formatting as needed.

4.  **Save:** The agent saves the changes to the file.

5.  **Recalculate Formulas:** If formulas were used, the agent uses the `recalc.py` script to recalculate all formulas in the spreadsheet.

6.  **Verify:** The agent verifies the output and fixes any errors.

## Authentication

The `xlsx` skill does not have any direct authentication requirements. The tools and libraries it uses (`pandas`, `openpyxl`, and `recalc.py`) are all local and do not require API keys or tokens. However, the skill does have a number of dependencies that must be installed in the environment for it to function correctly, including `pandas`, `openpyxl`, and `libreoffice`.
