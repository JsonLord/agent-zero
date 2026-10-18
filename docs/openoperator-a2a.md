# OpenOperator A2A Integration Contract

OpenOperator exposes autonomous integration points using the authenticated FastA2A JSON-RPC protocol over HTTPS.

## Service Discovery

Begin integration by requesting these read-only routes:

- **Health:** `GET /health`
- **OpenOperator docs:** `GET /docs`
- **Machine-readable A2A docs:** `GET /docs/a2a.json`
- **Agent Card:** `GET /a2a/.well-known/agent.json`
- **Compatibility Agent Card:** `GET /a2a/.well-known/agent-card.json`
- **FastA2A library docs:** `GET /a2a/docs`

## A2A JSON-RPC

- **A2A JSON-RPC Endpoint:** `POST /a2a/`

### Critical Routing Warning

`message/send`, `tasks/get`, and `tasks/cancel` are **JSON-RPC method names sent in the POST body**.

They are **NOT HTTP URL paths**.

Explicitly mark these as incorrect and they will return HTTP 404/405:
- `/a2a/message/send`
- `/a2a/tasks/get`
- `/a2a/agent-card`

Document the canonical JSON-RPC endpoint exactly as: `/a2a/`. Clients should not depend on redirect behavior.

### FastA2A 0.5 Wire Casing

The JSON wire format uses **camelCase** aliases. Do not use snake_case for A2A protocol parameters.

Correct:
```json
{
  "messageId": "msg-1",
  "acceptedOutputModes": ["application/json"]
}
```

Incorrect:
```json
{
  "message_id": "msg-1",
  "accepted_output_modes": ["application/json"]
}
```

Required camelCase fields include:
- `messageId`
- `contextId`
- `acceptedOutputModes`
- `historyLength`

## Authentication

OpenOperator supports two primary authentication schemes using the canonical deployment secret (`SPYNEL_AGENT_ZERO_API_KEY`).

- HTTP Bearer: `Authorization: Bearer <secret>`
- X-API-KEY: `X-API-KEY: <secret>`

Never expose this credential.

## Argus Capability

The `argus-supervisor` profile provides dedicated read-only functions to supervise OpenTraining.

Currently supported operational capabilities over A2A (when `ARGUS_SUPERVISOR_ENABLED=1`):
- `supervisor.health`
- `supervisor.status`
- `campaign.list`

Future capabilities (NOT currently supported over A2A):
- `campaign.create`
- `campaign.claim`
- `campaign.release`
- `campaign.submit`
- `campaign.intervene`
- `campaign.cancel`
- `campaign.mission`
- `campaign.answer`
- `campaign.resolve_intent`

### Canonical Argus Extension Envelope

The extension envelope correctly uses the URN namespace and canonical `requestId`:

```json
{
  "urn:openoperator:argus-supervisor:v1": {
    "operation": "supervisor.health",
    "requestId": "req-1"
  }
}
```

### Exact Argus Request Example

This copy-paste-safe example uses environment variables instead of literal tokens:

```bash
curl -X POST "$OPENOPERATOR_URL/a2a/" \
  -H "Authorization: Bearer $SPYNEL_AGENT_ZERO_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "id": "argus-health-1",
    "method": "message/send",
    "params": {
      "configuration": {
        "blocking": true,
        "acceptedOutputModes": ["application/json"]
      },
      "message": {
        "role": "user",
        "kind": "message",
        "messageId": "argus-health-1",
        "extensions": [
          "urn:openoperator:argus-supervisor:v1"
        ],
        "metadata": {
          "urn:openoperator:argus-supervisor:v1": {
            "operation": "supervisor.health",
            "requestId": "argus-health-1"
          }
        },
        "parts": [
          {
            "kind": "data",
            "data": {
              "params": {}
            }
          }
        ]
      }
    }
  }'
```
