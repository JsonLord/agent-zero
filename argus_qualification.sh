#!/usr/bin/env bash

TARGET="https://leon4gr45-openoperator.hf.space"
API_KEY="*laugh*"
SHA="1cd0489b8a5236bc1aaafbf7de01a93842d71896"

echo "Gate 0 - Health"
curl -s "$TARGET/health"

echo -e "\n\nGate 1 - Agent Card"
curl -s -H "Authorization: Bearer $API_KEY" "$TARGET/a2a/agent-card"

echo -e "\n\nGate 2 - supervisor.health"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "extensions": [
      {
        "namespace": "urn:openoperator:argus-supervisor:v1",
        "operation": "supervisor.health",
        "configuration": {
          "blocking": true,
          "accepted_output_modes": ["application/json"]
        }
      }
    ],
    "parts": [{"kind": "text", "text": "supervisor.health"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 3 - supervisor.status"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "extensions": [
      {
        "namespace": "urn:openoperator:argus-supervisor:v1",
        "operation": "supervisor.status",
        "configuration": {
          "blocking": true,
          "accepted_output_modes": ["application/json"]
        }
      }
    ],
    "parts": [{"kind": "text", "text": "supervisor.status"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 4 - campaign.list"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "extensions": [
      {
        "namespace": "urn:openoperator:argus-supervisor:v1",
        "operation": "campaign.list",
        "configuration": {
          "blocking": true,
          "accepted_output_modes": ["application/json"]
        }
      }
    ],
    "parts": [{"kind": "text", "text": "campaign.list"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 5 - generic regression"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "parts": [{"kind": "text", "text": "Reply only with GENERAL_A2A_OK"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 6 - malformed envelope"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "extensions": [
      {
        "namespace": "urn:openoperator:argus-supervisor:v1",
        "configuration": {
          "blocking": true,
          "accepted_output_modes": ["application/json"]
        }
      }
    ],
    "parts": [{"kind": "text", "text": "malformed"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 7 - unknown operation"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "message": {
    "extensions": [
      {
        "namespace": "urn:openoperator:argus-supervisor:v1",
        "operation": "unknown.op",
        "configuration": {
          "blocking": true,
          "accepted_output_modes": ["application/json"]
        }
      }
    ],
    "parts": [{"kind": "text", "text": "unknown.op"}]
  }
}' "$TARGET/a2a/message/send"

echo -e "\n\nGate 8 - Auth"
echo "Missing:"
curl -s -X POST "$TARGET/a2a/message/send"
echo -e "\nWrong:"
curl -s -X POST -H "Authorization: Bearer wrong-key" "$TARGET/a2a/message/send"
