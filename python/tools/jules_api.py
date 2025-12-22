import os
import requests
import json
from python.helpers.tool import Tool, Response

class JulesAPI(Tool):
    """
    A tool for interacting with the Jules API.
    """

    async def execute(self, **kwargs):
        """
        Executes a Jules API command.
        """
        api_key = os.environ.get("JULES_API_KEY")
        if not api_key:
            return Response(message="Error: JULES_API_KEY environment variable not set.", break_loop=False)

        command = self.args.get("command")
        if not command:
            return Response(message="Error: No command provided to jules_api tool.", break_loop=False)

        self.api_key = api_key
        self.base_url = "https://jules.googleapis.com/v1alpha"

        command_map = {
            "list_sources": self._list_sources,
            "create_session": self._create_session,
            "list_sessions": self._list_sessions,
            "approve_plan": self._approve_plan,
            "list_activities": self._list_activities,
            "send_message": self._send_message,
        }

        if command not in command_map:
            return Response(message=f"Error: Unknown command '{command}'.", break_loop=False)

        return await command_map[command]()

    def _make_request(self, method, endpoint, data=None):
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/{endpoint}"
        try:
            if isinstance(data, str):
                data = json.loads(data)
            response = requests.request(method, url, headers=headers, json=data)
            response.raise_for_status()
            return Response(message=response.text, break_loop=False)
        except requests.exceptions.RequestException as e:
            return Response(message=f"Error: API request failed: {e}", break_loop=False)
        except json.JSONDecodeError as e:
            return Response(message=f"Error: Invalid JSON in 'data' argument: {e}", break_loop=False)


    async def _list_sources(self):
        return self._make_request("GET", "sources")

    async def _create_session(self):
        data = self.args.get("data")
        if not data:
            return Response(message="Error: 'data' argument is required for create_session.", break_loop=False)
        return self._make_request("POST", "sessions", data=data)

    async def _list_sessions(self):
        page_size = self.args.get("pageSize", 5)
        return self._make_request("GET", f"sessions?pageSize={page_size}")

    async def _approve_plan(self):
        session_id = self.args.get("session_id")
        if not session_id:
            return Response(message="Error: 'session_id' is required for approve_plan.", break_loop=False)
        return self._make_request("POST", f"sessions/{session_id}:approvePlan")

    async def _list_activities(self):
        session_id = self.args.get("session_id")
        if not session_id:
            return Response(message="Error: 'session_id' is required for list_activities.", break_loop=False)
        page_size = self.args.get("pageSize", 30)
        return self._make_request("GET", f"sessions/{session_id}/activities?pageSize={page_size}")

    async def _send_message(self):
        session_id = self.args.get("session_id")
        if not session_id:
            return Response(message="Error: 'session_id' is required for send_message.", break_loop=False)
        data = self.args.get("data")
        if not data:
            return Response(message="Error: 'data' is required for send_message.", break_loop=False)
        return self._make_request("POST", f"sessions/{session_id}:sendMessage", data=data)
