#!/usr/bin/env bash
TARGET="https://leon4gr45-openoperator.hf.space"
API_KEY="Elzheimer"

echo "Gate 2 - supervisor.health"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
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
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "metadata": {
        "urn:openoperator:argus-supervisor:v1": {
          "operation": "supervisor.health",
          "request_id": "argus-health-1"
        }
      },
      "parts": [{"kind": "text", "text": "supervisor.health"}]
    }
  }
}' "$TARGET/a2a/"
