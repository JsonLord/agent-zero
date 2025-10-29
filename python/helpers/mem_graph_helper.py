import requests
import json
import uuid

class MemGraphHelper:
    """
    A class to manage persistent chat history using the MCP Knowledge Graph service.
    """
    def __init__(self, base_url="https://harvesthealth-mem-graph.hf.space/mcp"):
        self.api_url = base_url
        self.headers = {"Content-Type": "application/json"}

    def _send_command(self, command: str) -> dict:
        """Helper function to send commands to the memory service."""
        payload = {"command": command}
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return {"error": str(e)}

    def load_history(self, conversation_id: str) -> list:
        """
        Loads chat history for a given conversation ID.
        Returns an empty list if no history is found.
        """
        key = f"chat_history:{conversation_id}"
        print(f"<- Loading history for key: {key}")

        response_data = self._send_command(f"GET {key}")

        if "response" in response_data and response_data["response"] != "(nil)":
            try:
                # The response is a JSON string, so we need to parse it
                return json.loads(response_data["response"])
            except json.JSONDecodeError:
                print("Error: Could not decode JSON from response.")
                return []
        return []

    def save_history(self, conversation_id: str, history: list):
        """
        Saves the chat history for a given conversation ID.
        """
        key = f"chat_history:{conversation_id}"
        # Convert the list of messages into a compact JSON string
        value = json.dumps(history)

        print(f"-> Saving history for key: {key}")

        response_data = self._send_command(f"SET {key} {value}")

        if "response" in response_data and response_data["response"] == "OK":
            print(" Save successful.")
        else:
            print(f" Save failed. Response: {response_data}")
