# Agent.md - Deployment & Best Practices Guide for Open Operator

This document informs autonomous agents and deployment managers about guidelines, configuration, and ongoing deployment best practices for running Open Operator on Hugging Face Spaces.

---

## 1. Deployment Configuration

### Target Space
- **Profile:** `Leon4gr45`
- **Space:** `openoperator`
- **Full Identifier:** `Leon4gr45/openoperator`
- **Frontend Port:** `7860` (mandatory for all Hugging Face Spaces)

### Deployment Method
- **SDK:** `docker`

### HF Token
- The environment variable `HF_TOKEN` (provided at runtime) is used for authentication.
- Never hardcode tokens in codebase. Always read from environment variables.

### Required Files
- `Dockerfile`: Configured with EXPOSE 7860 and Docker SDK runtime.
- `README.md`: Contains mandatory Hugging Face Space YAML frontmatter:
  ```yaml
  ---
  title: Open Operator
  sdk: docker
  app_port: 7860
  ---
  ```
- `.hfignore`: Excludes non-essential build/runtime files (`.git`, `.venv`, `usr/`, `tmp/`, `__pycache__`, etc.).
- `Agent.md`: This file, committed before deployment.

---

## 2. API Exposure and Documentation

### Mandatory Endpoints

#### /health
- **Method:** GET
- **Purpose:** Returns HTTP 200 JSON status when the application is ready. Required for Hugging Face to transition Space status from *starting* -> *running*.
- **Request Example:**
  `GET /health`
- **Response Example:**
  ```json
  {
    "status": "ok"
  }
  ```

#### /api-docs
- **Method:** GET
- **Purpose:** Documents all available API endpoints. Reachable at `https://leon4gr45-openoperator.hf.space/api-docs`.
- **Request Example:**
  `GET /api-docs`
- **Response Example:**
  ```json
  {
    "title": "Open Operator API Documentation",
    "description": "API documentation for Open Operator (Agent Zero)",
    "endpoints": [ ... ]
  }
  ```

### Functional Endpoints

#### /api/health
- **Method:** GET / POST
- **Purpose:** Detailed process health and git repository status info.
- **Request Example:**
  `GET /api/health`
- **Response Example:**
  ```json
  {
    "gitinfo": {
      "version": "v1.6",
      "commit_time": "2026-01-01 00:00:00"
    },
    "error": null
  }
  ```

#### /api/message
- **Method:** POST
- **Purpose:** Process synchronous message in specified agent context.
- **Request Example:**
  ```json
  {
    "message": "Hello Open Operator",
    "context_id": "default"
  }
  ```
- **Response Example:**
  ```json
  {
    "response": "Hello! How can I help you today?"
  }
  ```

#### /api/message_async
- **Method:** POST
- **Purpose:** Queue asynchronous message for background agent processing.
- **Request Example:**
  ```json
  {
    "message": "Start long-running task",
    "context_id": "default"
  }
  ```
- **Response Example:**
  ```json
  {
    "status": "queued"
  }
  ```

#### /api/settings_get
- **Method:** GET / POST
- **Purpose:** Retrieve system and user settings snapshot.
- **Request Example:**
  `GET /api/settings_get`
- **Response Example:**
  ```json
  {
    "settings": {
      "chat_model": "gpt-4o"
    }
  }
  ```

#### /api/settings_set
- **Method:** POST
- **Purpose:** Update system and user settings.
- **Request Example:**
  ```json
  {
    "settings": {
      "timezone": "UTC"
    }
  }
  ```
- **Response Example:**
  ```json
  {
    "success": true
  }
  ```

#### /api/chat_create
- **Method:** POST
- **Purpose:** Create a new chat session context.
- **Request Example:**
  ```json
  {
    "name": "Project Discussion"
  }
  ```
- **Response Example:**
  ```json
  {
    "context_id": "ctx-98765"
  }
  ```

#### /api/chat_remove
- **Method:** POST
- **Purpose:** Remove an existing chat session context.
- **Request Example:**
  ```json
  {
    "context_id": "ctx-98765"
  }
  ```
- **Response Example:**
  ```json
  {
    "success": true
  }
  ```

#### /api/chat_load
- **Method:** POST
- **Purpose:** Load conversation history for a chat context.
- **Request Example:**
  ```json
  {
    "context_id": "ctx-98765"
  }
  ```
- **Response Example:**
  ```json
  {
    "history": []
  }
  ```

#### /api/chat_reset
- **Method:** POST
- **Purpose:** Clear messages in active chat context.
- **Request Example:**
  ```json
  {
    "context_id": "ctx-98765"
  }
  ```
- **Response Example:**
  ```json
  {
    "success": true
  }
  ```

#### /api/history_get
- **Method:** GET / POST
- **Purpose:** Retrieve message history for active context.
- **Request Example:**
  `GET /api/history_get`
- **Response Example:**
  ```json
  {
    "history": []
  }
  ```

#### /api/upload
- **Method:** POST
- **Purpose:** Upload file to current context work directory.
- **Request Example:**
  Multipart form upload with `file` payload.
- **Response Example:**
  ```json
  {
    "filename": "data.csv",
    "path": "/a0/usr/workdir/data.csv"
  }
  ```

---

## 3. Deployment Workflow

### Precondition
Clean obsolete non-project files from target Space before upload:
```bash
hf upload Leon4gr45/openoperator . --repo-type=space --delete "*"
```

### Deployment Upload
Upload repository contents to Hugging Face Space:
```bash
hf upload Leon4gr45/openoperator --repo-type=space
```

### Monitoring Build & Run Logs
Stream build logs (SSE):
```bash
curl -N -H "Authorization: Bearer $HF_TOKEN" "https://huggingface.co/api/spaces/Leon4gr45/openoperator/logs/build"
```

Stream run logs (SSE):
```bash
curl -N -H "Authorization: Bearer $HF_TOKEN" "https://huggingface.co/api/spaces/Leon4gr45/openoperator/logs/run"
```

Iterate modifying codebase, redeploying, and monitoring logs until deployment is running and responding cleanly to `/health` and `/api-docs`.
