---
name: huggingface-cli
description: Hugging Face CLI (hf) usage for Spaces, Hub repositories, logs, and metadata.
---

# Hugging Face CLI Skill

## Capabilities

- Inspect authenticated identity: `hf auth whoami`
- Inspect Space status & info: `hf spaces info OWNER/SPACE`
- Stream or read Space runtime logs: `hf spaces logs OWNER/SPACE`
- Stream or read Space build logs: `hf spaces logs --build OWNER/SPACE`
- List secrets or variables: `hf spaces secrets list OWNER/SPACE`, `hf spaces variables list OWNER/SPACE`
- Upload/download Hub repository assets: `hf upload`, `hf download`

Always rely on `HF_TOKEN` from the environment.
