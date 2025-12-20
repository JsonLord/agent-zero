---
name: git
description: "Core skill for Git and GitHub operations. Use this skill to perform version control tasks, such as creating branches, committing changes, and creating pull requests using the `gh` CLI."
allowed-tools: [Bash, Write]
---

# Git

## Overview

This skill is designed to provide comprehensive support for Git and GitHub operations using the `gh` CLI. It enables the agent to perform a wide range of version control tasks, from creating branches to creating pull requests.

## Initial Setup

Before using this skill for the first time, you must ensure that the `gh` CLI is installed and authenticated.

1.  **Check for `gh`:**
    ```bash
    gh --version
    ```
    If this command fails, you need to install the `gh` CLI.

2.  **Check for authentication:**
    ```bash
    gh auth status
    ```
    If you are not logged in, you need to authenticate.

3.  **Follow the setup instructions:**
    If `gh` is not installed or you are not authenticated, you must follow the instructions in the `setup.md` file before proceeding.

## When to Use This Skill

This skill should be used when:
- A file needs to be edited.
- A new branch needs to be created.
- Changes need to be committed.
- A pull request needs to be created.

## Core Workflow

1.  **Create a new branch:**
    ```bash
    git checkout -b <branch-name>
    ```

2.  **Apply the file edits:**
    *   Use the `write` tool to apply the necessary changes to the file.

3.  **Commit the changes:**
    ```bash
    git add .
    git commit -m "<commit-message>"
    ```

4.  **Push the changes:**
    ```bash
    git push -u origin <branch-name>
    ```

5.  **Create a pull request:**
    ```bash
    gh pr create --title "<pr-title>" --body "<pr-body>"
    ```
