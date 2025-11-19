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

        endpoint = self.args.get("endpoint", "")
        if not endpoint:
            return Response(message="Error: No endpoint provided to jules_api tool.", break_loop=False)

        method = self.args.get("method", "GET").upper()
        data = self.args.get("data", None)

        headers = {
            "X-Goog-Api-Key": api_key,
            "Content-Type": "application/json"
        }

        url = f"https://jules.googleapis.com/v1alpha/{endpoint}"

        try:
            response = requests.request(method, url, headers=headers, data=data)
            response.raise_for_status()  # Raise an exception for bad status codes
            return Response(message=response.text, break_loop=False)
        except requests.exceptions.RequestException as e:
            return Response(message=f"Error: API request failed: {e}", break_loop=False)
