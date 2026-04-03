---
title: OpenOperator Agent-Zero
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Agent-Zero Deployment on Hugging Face Spaces

This space runs a modified version of **Agent-Zero**, adapted for Hugging Face Spaces. It automatically pulls the latest version from the main branch on startup while maintaining custom adaptations for API accessibility and non-root environment compatibility.

## Key Adaptations

1.  **Authentication & CSRF Bypass**: Security is adjusted for Hugging Face's environment to allow public API access via `https://Leon4gr45-openoperator.hf.space`.
2.  **Health Check & API Documentation**: Mandatory endpoints `/health` and `/api-docs` are available at the root.
3.  **Port Mapping**: The application is configured to listen on port 7860, as required by the Space.
4.  **Runtime Logic**: The system automatically identifies the Dockerized environment and adjusts paths and settings accordingly.

## API Endpoints

-   **Health**: `/health`
-   **API Documentation**: `/api-docs`
-   **Core API**: `/api/message` (requires JSON payload)
