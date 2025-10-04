import json
import subprocess
from python.helpers import persist_chat
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent import AgentContext

# Replace with your actual MCP server URL
MCP_SERVER_URL = "https://harvesthealth-neo4j-mcp-agent-memory.hf.space/mcp/"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

def send_chat_to_mcp(context: 'AgentContext'):
    """
    Serializes the agent context and sends it to the MCP server using the 'create_entities' tool.
    """
    try:
        chat_json = persist_chat.export_json_chat(context)

        # Use a timestamp to be able to retrieve the latest chat
        timestamp = datetime.utcnow().isoformat()

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "create_entities",
                "inputs": {
                    "entities": [
                        {
                            "name": "ChatHistory",
                            "type": "Log",
                            "observations": [chat_json],
                            "timestamp": timestamp
                        }
                    ]
                }
            },
            "id": f"store-chat-{timestamp}"
        }

        curl_command = [
            'curl', '-X', 'POST',
            '-H', 'Content-Type: application/json',
            '-H', 'Accept: application/json, text/event-stream',
            '-d', json.dumps(payload),
            MCP_SERVER_URL
        ]

        print(f"Sending chat to MCP server...")

        result = subprocess.run(curl_command, capture_output=True, text=True)

        if result.returncode == 0:
            print("Successfully sent chat to MCP server.")
            # print("Response:", result.stdout)
        else:
            print(f"Error sending chat to MCP server: {result.stderr}")

    except Exception as e:
        print(f"An error occurred while sending chat to MCP server: {e}")

def get_chat_from_mcp() -> str | None:
    """
    Retrieves the last chat from the MCP server using the 'read_graph' tool.
    """
    try:
        # The query needs to be adapted to how the 'create_entities' tool actually stores the data.
        # Based on the previous implementation, we assume a 'timestamp' property is available for sorting.
        # The property name in the query must match what is being stored.
        # We will assume the node is labeled 'Entity' and has properties 'type' and 'name'.
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "read_graph",
                "inputs": {
                    "query": "MATCH (e:Entity {type: 'Log', name: 'ChatHistory'}) RETURN e.observations AS history, e.timestamp AS timestamp ORDER BY e.timestamp DESC LIMIT 1"
                }
            },
            "id": "get-chat-01"
        }

        curl_command = [
            'curl', '-X', 'POST',
            '-H', 'Content-Type: application/json',
            '-H', 'Accept: application/json, text/event-stream',
            '-d', json.dumps(payload),
            MCP_SERVER_URL
        ]

        print(f"Retrieving chat from MCP server...")

        result = subprocess.run(curl_command, capture_output=True, text=True)

        if result.returncode == 0:
            response_data = json.loads(result.stdout)
            if 'result' in response_data and 'data' in response_data['result']:
                records = response_data['result']['data']
                if records:
                    # Assuming the history is in the 'history' field of the first record
                    chat_history_list = records[0].get('history')
                    if chat_history_list and isinstance(chat_history_list, list) and len(chat_history_list) > 0:
                        print("Successfully retrieved chat from MCP server.")
                        return chat_history_list[0]

            print("No chat history found on MCP server.")
            return None
        else:
            print(f"Error retrieving chat from MCP server: {result.stderr}")
            return None

    except Exception as e:
        print(f"An error occurred while retrieving chat from MCP server: {e}")
        return None