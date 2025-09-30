import argparse
import json
import os
import requests
import sys

def get_config(server_name):
    """
    Reads the configuration from conf/mcp_config.json.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'conf', 'mcp_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    if server_name in config['servers']:
        return config['servers'][server_name]
    elif 'default' in config:
        return config['default']
    else:
        raise ValueError(f"Server '{server_name}' not found in config and no default is set.")

def initialize_session(server_name):
    """
    Initializes a session with the MCP server and returns the session ID.
    """
    config = get_config(server_name)
    endpoint = config['endpoint']
    bearer_token = os.getenv(config['bearer_token'], config['bearer_token'])


    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {bearer_token}"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "AgentZeroClient",
                "version": "1.0.0"
            },
            "capabilities": {}
        }
    }

    response = requests.post(endpoint, headers=headers, json=payload)
    response.raise_for_status()

    session_id = response.headers.get("mcp-session-id")
    if not session_id:
        raise ValueError("mcp-session-id not found in response headers")

    print(session_id)

def list_tools(server_name, session_id):
    """
    Lists the available tools on the MCP server.
    """
    config = get_config(server_name)
    endpoint = config['endpoint']
    bearer_token = os.getenv(config['bearer_token'], config['bearer_token'])

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {bearer_token}",
        "mcp-session-id": session_id
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    response = requests.post(endpoint, headers=headers, json=payload)
    response.raise_for_status()
    print(response.text)


def call_tool(server_name, session_id, tool_name, tool_args):
    """
    Calls a specific tool on the MCP server.
    """
    config = get_config(server_name)
    endpoint = config['endpoint']
    bearer_token = os.getenv(config['bearer_token'], config['bearer_token'])

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {bearer_token}",
        "mcp-session-id": session_id
    }

    try:
        arguments = json.loads(tool_args)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format for arguments.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    response = requests.post(endpoint, headers=headers, json=payload)
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Client for Agent-Zero")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Initialize command
    parser_init = subparsers.add_parser("initialize", help="Initialize a new MCP session.")
    parser_init.add_argument("server_name", help="The name of the server from the config file.")

    # List tools command
    parser_list = subparsers.add_parser("list_tools", help="List available tools.")
    parser_list.add_argument("server_name", help="The name of the server from the config file.")
    parser_list.add_argument("session_id", help="The mcp-session-id.")

    # Call tool command
    parser_call = subparsers.add_parser("call_tool", help="Call a specific tool.")
    parser_call.add_argument("server_name", help="The name of the server from the config file.")
    parser_call.add_argument("session_id", help="The mcp-session-id.")
    parser_call.add_argument("tool_name", help="The name of the tool to call.")
    parser_call.add_argument("tool_args", help="The arguments for the tool in JSON format.")

    args = parser.parse_args()

    if args.command == "initialize":
        initialize_session(args.server_name)
    elif args.command == "list_tools":
        list_tools(args.server_name, args.session_id)
    elif args.command == "call_tool":
        call_tool(args.server_name, args.session_id, args.tool_name, args.tool_args)