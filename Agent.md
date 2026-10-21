## 1. Deployment Configuration

### Target Space
- **Profile:** `Leon4gr45`
- **Space:** `opentraining`
- **Full Identifier:** `Leon4gr45/opentraining`
- **Frontend Port:** `7860` (mandatory for all Hugging Face Spaces)

### Deployment Method
- **Docker SDK** — for all other applications (recommended default for flexibility)

### Authentication & API Routes
The `OpenTraining` space implements standard OpenOperator A2A JSON-RPC 2.0 endpoints under the base path `/a2a/`.
All A2A requests must be authenticated via an HTTP Bearer token or `X-API-KEY`.

#### Discovery
- `/health`
- `/docs`
- `/docs/a2a.json`
- `/api-docs`
- `/a2a/.well-known/agent.json`
- `/a2a/.well-known/agent-card.json`

#### Valid JSON-RPC methods on POST /a2a/
- `message/send`
- `tasks/get`
- `tasks/cancel`

Legacy paths like `/a2a/message/send` or `/a2a/tasks/get` will return `404 Not Found`.

### Container Startup Chain
- `Dockerfile`
- `start_openoperator.sh`
- `docker/hf/initialize_hf.sh`
- `scripts/configure_hf_a2a.py`
- `prepare.py`
- `supervisord`
- `run_ui.py`
