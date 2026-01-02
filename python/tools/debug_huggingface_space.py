from python.helpers.tool import Tool, Response
from huggingface_hub import constants
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status
from python.helpers.huggingface_auth import ensure_huggingface_auth


class DebugHuggingFaceSpace(Tool):
    """
    A tool to debug Hugging Face Spaces.
    """

    async def execute(self, space_id: str, **kwargs) -> Response:
        """
        Performs diagnostic checks on a given Hugging Face Space.
        """
        if not await ensure_huggingface_auth(self.agent):
            return Response(message="Hugging Face authentication failed. Cannot debug space.", break_loop=False)

        try:
            # Check 1: Attempt to fetch a JWT token
            jwt_url = f"{constants.ENDPOINT}/api/spaces/{space_id}/jwt"
            response = get_session().get(jwt_url, headers=build_hf_headers())
            hf_raise_for_status(response)
            jwt_token = response.json()["token"]

            return Response(message=f"Successfully fetched JWT token for Space '{space_id}'.", break_loop=False)
        except Exception as e:
            return Response(message=f"Error fetching JWT token for Space '{space_id}': {e}", break_loop=False)
