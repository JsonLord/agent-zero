from python.helpers.tool import Tool, Response
from huggingface_hub import HfApi
from python.helpers.huggingface_auth import ensure_huggingface_auth


class HuggingFaceSpaceActions(Tool):
    """
    A tool to inspect a Hugging Face Space and determine available actions.
    """

    async def execute(self, space_id: str, **kwargs) -> Response:
        """
        Inspects a Space's files to determine the available API endpoints and actions.
        """
        if not await ensure_huggingface_auth(self.agent):
            return Response(message="Hugging Face authentication failed. Cannot inspect space.", break_loop=False)

        try:
            hf_api = HfApi()
            files = hf_api.list_repo_files(repo_id=space_id, repo_type="space")

            actions = []
            if "app.py" in files:
                actions.append("Inspect `app.py` for Gradio or FastAPI endpoints.")
            if "README.md" in files:
                actions.append("Inspect `README.md` for API documentation.")

            if not actions:
                return Response(message=f"Could not determine any actions for Space '{space_id}'.", break_loop=False)

            return Response(message=f"Available actions for Space '{space_id}':\n" + "\n".join(actions), break_loop=False)
        except Exception as e:
            return Response(message=f"Error inspecting Space '{space_id}': {e}", break_loop=False)
