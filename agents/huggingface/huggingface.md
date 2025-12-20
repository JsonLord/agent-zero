---
name: huggingface
description: "Core skill for Hugging Face Hub operations. Use this skill to perform model and dataset tasks, such as uploading files and creating repositories using the `hf` CLI."
allowed-tools: [Bash, Write]
---

# Hugging Face

## Overview

This skill is designed to provide comprehensive support for Huggng Face Hub operations using the `hf` CLI. It enables the agent to perform a wide range of tasks, from creating repositories to uploading files.

## Initial Setup

Before using this skill for the first time, you must ensure that the `hf` CLI is installed and authenticated.

1.  **Check for `hf`:**
    ```bash
    hf --version
    ```
    If this command fails, you need to install the `hf` CLI.

2.  **Check for authentication:**
    ```bash
    hf whoami
    ```
    If you are not logged in, you need to authenticate.

3.  **Follow the setup instructions:**
    If `hf` is not installed or you are not authenticated, you must follow the instructions in the `setup.md` file before proceeding.

## When to Use This Skill

This skill should be used when:
- A file needs to be uploaded to the Hugging Face Hub.
- A new repository needs to be created on the Hugging Face Hub.

## Core Workflow

1.  **Create a new repository (if it doesn't exist):**
    ```bash
    hf repo create <repo-id> --type <repo-type>
    ```
    *   `<repo-id>` is the name of the repository (e.g., `my-cool-model`).
    *   `<repo-type>` is the type of repository (`model`, `dataset`, or `space`).

2.  **Apply the file edits:**
    *   Use the `write` tool to create or modify the files you want to upload.

3.  **Upload the files:**
    ```bash
    hf upload <repo-id> <local-path> <path-in-repo>
    ```
    *   `<repo-id>` is the name of the repository.
    *   `<local-path>` is the path to the local file or folder to upload.
    *   `<path-in-repo>` is the path where the file or folder should be placed in the repository.
