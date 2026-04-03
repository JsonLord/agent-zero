# Agent Zero Hugging Face Deployment

This space runs Agent Zero with API adaptations.

## Tricks and Ongoing Deployment Best Practices

- **SDK:** Always use the Docker SDK for flexibility.
- **Port:** Port 7860 is mandatory.
- **Environment:** Set `HF_SPACE=true` to enable adaptations.
- **Codebase:** The `start_hf.sh` script clones the repository at runtime to ensure the latest version.
- **API Access:** Authentication and CSRF are bypassed when `HF_SPACE=true`.

## Mandatory Endpoints

- **`/api/health`**: Returns HTTP 200 when the app is ready.
- **`/api/api-docs`**: Documents all available API endpoints.

## Functional Endpoints

### /api/message
- **Method**: POST
- **Purpose**: Send a message to the agent.
- **Request**:
  ```json
  {
    "text": "hello",
    "context": "optional_context_id"
  }
  ```
- **Response**:
  ```json
  {
    "message": "...",
    "context": "..."
  }
  ```
