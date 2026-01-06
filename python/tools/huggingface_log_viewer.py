import json
from typing import Literal

from huggingface_hub import constants
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status

from python.helpers.tool import Tool

class HuggingfaceLogViewer(Tool):
    """
    A tool for viewing logs from Hugging Face Spaces.
    """

    def __init__(self, agent, **kwargs):
        super().__init__(agent, "huggingface_log_viewer", **kwargs)

    async def execute(self, space_id: str, level: Literal["build", "run"] = "run", **kwargs):
        """
        Fetches and streams logs from a Hugging Face Space.
        """
        try:
            # fetch a JWT token to access the API
            jwt_url = f"{constants.ENDPOINT}/api/spaces/{space_id}/jwt"
            response = get_session().get(jwt_url, headers=build_hf_headers())
            hf_raise_for_status(response)
            jwt_token = response.json()["token"]

            # fetch the logs
            logs_url = f"https://api.hf.space/v1/{space_id}/logs/{level}"

            log_output = []
            with get_session().get(logs_url, headers=build_hf_headers(token=jwt_token), stream=True) as response:
                hf_raise_for_status(response)
                for line in response.iter_lines():
                    if not line.startswith(b"data: "):
                        continue
                    line_data = line[len(b"data: "):]
                    try:
                        event = json.loads(line_data.decode())
                        log_output.append(f"{event['timestamp']}: {event['data']}")
                    except json.JSONDecodeError as e:
                        print(e)
                        continue
            return "\n".join(log_output)
        except Exception as e:
            return f"Error fetching logs: {e}"
