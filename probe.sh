#!/usr/bin/env bash
TARGET="https://leon4gr45-openoperator.hf.space"
API_KEY="Elzheimer"

echo "1. GET /a2a/.well-known/agent.json"
curl -s -i "$TARGET/a2a/.well-known/agent.json" -H "Authorization: Bearer $API_KEY"
echo -e "\n\n2. GET /a2a/docs"
curl -s -i "$TARGET/a2a/docs" -H "Authorization: Bearer $API_KEY"
echo -e "\n\n3. POST /a2a/ message/send"
curl -s -i -X POST "$TARGET/a2a/" -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" --data '{
  "jsonrpc": "2.0",
  "id": "argus-health-1",
  "method": "message/send",
  "params": {
    "configuration": {"blocking": true, "accepted_output_modes": ["application/json"]},
    "message": {
      "role": "user",
      "kind": "message",
      "message_id": "argus-health-1",
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "metadata": {
        "urn:openoperator:argus-supervisor:v1": {
          "operation": "supervisor.health",
          "request_id": "argus-health-1"
        }
      },
      "parts": [{"kind": "data", "data": {"params": {}}}]
    }
  }
}'
