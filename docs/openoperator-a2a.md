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

## Capability identity and read-only limits

Use skill `id` as identity, never its display name. Disabled Argus advertises only
`general_assistance`. Enabled Argus advertises that skill plus
`argus_supervisor_health`, `argus_supervisor_status` and `argus_campaign_list`.
`argus_campaign_control` is not advertised or accepted by this extension.
The read operations bypass Agent Zero initialization and all model calls, including
when no Argus backend is configured. Installation of the `argus-supervisor` profile
is asserted separately from runtime enablement.

Malformed envelopes return `invalid_argus_envelope`, disabled mode returns
`argus_supervisor_disabled`, unsupported operations return
`unsupported_argus_operation`, and internal failures return
`argus_supervisor_unavailable`. Error details do not include exception strings.
Legacy `request_id` is accepted; responses use `requestId`.

The incoming HF authority remains `SPYNEL_AGENT_ZERO_API_KEY` for API, MCP and A2A.
Outgoing OpenTraining still uses the existing OpenTrainingA2AClient and
OPENTRAINING_A2A_URL / OPENTRAINING_A2A_TOKEN / OPENTRAINING_A2A_PROJECT.
No incoming OPENOPERATOR_A2A_TOKEN authority is introduced.

The historical streaming flag is retained in this source reconstruction for parity;
this PR does not qualify streaming or campaign-control mutations. Standard task
cancellation is not authority to control a training campaign.

For a bounded read-only deployment smoke, run `scripts/qualify_openoperator_a2a.sh`
with the canonical key securely configured and EXPECTED_SOURCE_SHA set to the exact
clean deployment commit. The script prints assertion names, not credentials or raw
authenticated responses. It never starts training, acquires a controller or runs a
model-driven campaign. The separate Spynel observer-chain smoke requires an existing
production observer task/campaign and must leave controller identity/epoch absent.
