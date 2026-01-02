import json
from typing import Literal
from python.helpers.tool import Tool, Response
from huggingface_hub import constants
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status
from python.helpers.huggingface_auth import ensure_huggingface_auth


class HuggingFaceLogs(Tool):
    """
    A tool to fetch logs from Hugging Face Spaces.
    """

    async def execute(self, space_id: str, level: Literal["build", "run"] = "run", **kwargs) -> Response:
        """
        Fetches logs for a given Hugging Face Space.
        """
        if not await ensure_huggingface_auth(self.agent):
            return Response(message="Hugging Face authentication failed. Cannot fetch logs.", break_loop=False)

        try:
            # fetch a JWT token to access the API
            jwt_url = f"{constants.ENDPOINT}/api/spaces/{space_id}/jwt"
            response = get_session().get(jwt_url, headers=build_hf_headers())
            hf_raise_for_status(response)
            jwt_token = response.json()["token"]

            # fetch the logs
            logs_url = f"https://api.hf.space/v1/{space_id}/logs/{level}"

            logs = []
            with get_session().get(logs_url, headers=build_hf_headers(token=jwt_token), stream=True) as response:
                hf_raise_for_status(response)
                for line in response.iter_lines():
                    if not line.startswith(b"data: "):
                        continue
                    line_data = line[len(b"data: "):]
                    try:
                        event = json.loads(line_data.decode())
                        logs.append(f"{event['timestamp']} {event['data']}")
                    except json.JSONDecodeError:
                        continue

            return Response(message="\n".join(logs), break_loop=False)
        except Exception as e:
            return Response(message=f"Error fetching logs: {e}", break_loop=False)
