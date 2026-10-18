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

echo -e "\n\nGate 3 - supervisor.status"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "argus-status-1",
  "method": "message/send",
  "params": {
    "configuration": {
      "blocking": true,
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "argus-status-1",
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "metadata": {
        "urn:openoperator:argus-supervisor:v1": {
          "operation": "supervisor.status",
          "request_id": "argus-status-1"
        }
      },
      "parts": [{"kind": "text", "text": "supervisor.status"}]
    }
  }
}' "$TARGET/a2a/"

echo -e "\n\nGate 4 - campaign.list"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "argus-list-1",
  "method": "message/send",
  "params": {
    "configuration": {
      "blocking": true,
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "argus-list-1",
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "metadata": {
        "urn:openoperator:argus-supervisor:v1": {
          "operation": "campaign.list",
          "request_id": "argus-list-1"
        }
      },
      "parts": [{"kind": "text", "text": "campaign.list"}]
    }
  }
}' "$TARGET/a2a/"

echo -e "\n\nGate 5 - generic regression"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "regress-1",
  "method": "message/send",
  "params": {
    "configuration": {
      "blocking": true,
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "regress-1",
      "parts": [{"kind": "text", "text": "Reply only with GENERAL_A2A_OK"}]
    }
  }
}' "$TARGET/a2a/"

echo -e "\n\nGate 6 - malformed envelope"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "malformed-1",
  "method": "message/send",
  "params": {
    "configuration": {
      "blocking": true,
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "malformed-1",
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "parts": [{"kind": "text", "text": "malformed"}]
    }
  }
}' "$TARGET/a2a/"

echo -e "\n\nGate 7 - unknown operation"
curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0",
  "id": "unknown-1",
  "method": "message/send",
  "params": {
    "configuration": {
      "blocking": true,
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "unknown-1",
      "extensions": ["urn:openoperator:argus-supervisor:v1"],
      "metadata": {
        "urn:openoperator:argus-supervisor:v1": {
          "operation": "unknown.op",
          "request_id": "unknown-1"
        }
      },
      "parts": [{"kind": "text", "text": "unknown.op"}]
    }
  }
}' "$TARGET/a2a/"
