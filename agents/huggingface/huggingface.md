---
name: huggingface
description: "A skill for deploying applications to Hugging Face Spaces and monitoring their status."
allowed-tools: [deploy_to_hf_space, huggingface_logs]
---

# Hugging Face Deployment

## Overview

This skill is designed to provide a robust and reliable workflow for deploying applications to Hugging Face Spaces. It uses a dedicated tool, `deploy_to_hf_space`, which orchestrates a multi-step, git-based deployment process.

## When to Use This Skill

This skill should be used when:
- A GitHub repository needs to be deployed to a Hugging Face Space.
- The build and runtime status of a Hugging Face Space needs to be monitored.

## Core Workflows

### Deploying a GitHub Repository to a Hugging Face Space

This workflow uses the `deploy_to_hf_space` tool to manage the entire deployment process.

1.  **Invoke the `deploy_to_hf_space` tool with the required parameters:**
    - `space_id`: The ID of the Hugging Face Space (e.g., "YourUser/YourSpace").
    - `github_repo_url`: The URL of the source GitHub repository.
    - `secrets`: A JSON string of a dictionary containing the secrets to be set.
    - `requirements_generator_command` (optional): A command to run to generate a `requirements.txt` file.
    - `start_script_content` (optional): The content for a `start.sh` script. **Note:** Hugging Face Spaces expect the application to be served on port 7860. Ensure your startup command reflects this (e.g., `python run_ui.py --port 7860`).

2.  **Monitor the deployment:**
    - After the `deploy_to_hf_space` tool completes, use the `huggingface_logs` tool to monitor the build and runtime logs of the Space.

### Monitoring a Hugging Face Space

This workflow uses the `huggingface_logs` tool to retrieve the logs for a Space.

1.  **Invoke the `huggingface_logs` tool with the required parameters:**
    - `space_id`: The ID of the Hugging Face Space (e.g., "YourUser/YourSpace").
    - `level`: The log level to retrieve ("build" or "run").

2.  **Analyze the logs:**
    - Examine the logs for any errors or messages that indicate the status of the Space.
