#!/usr/bin/env bash
# Qualification script for OpenOperator A2A integration

set -eo pipefail

: "${SPYNEL_AGENT_ZERO_API_KEY:?SPYNEL_AGENT_ZERO_API_KEY is required}"
: "${TARGET:=https://leon4gr45-openoperator.hf.space}"

echo "Starting OpenOperator A2A Qualification against $TARGET"

echo -e "\n1. GET /health"
curl -s -f "$TARGET/health"

echo -e "\n\n2. GET /docs/a2a.json"
curl -s -f "$TARGET/docs/a2a.json"

echo -e "\n\n3. GET /a2a/.well-known/agent.json"
curl -s -f -H "Authorization: Bearer $SPYNEL_AGENT_ZERO_API_KEY" "$TARGET/a2a/.well-known/agent.json"

echo -e "\n\n4. POST /a2a/ message/send - supervisor.health"
curl -s -i -X POST "$TARGET/a2a/" \
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

echo -e "\n\n5. POST /a2a/ message/send - malformed wire schema"
curl -s -i -X POST "$TARGET/a2a/" \
  -H "Authorization: Bearer $SPYNEL_AGENT_ZERO_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "id": "malformed",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "kind": "message",
        "message_id": "malformed",
        "parts": [{"kind": "text", "text": "bad snake case"}]
      }
    }
  }'

echo -e "\n\nQualification finished."
