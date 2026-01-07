import os
import json
from huggingface_hub import HfApi, Repository
from python.helpers.tool import Tool, Response

class DeployToHfSpace(Tool):
    """
    A dedicated tool to deploy a local directory to a Hugging Face Space,
    including setting secrets. This tool is more robust than using git commands.
    """

    async def execute(self, space_id: str, local_path: str, secrets: str, **kwargs) -> Response:
        """
        Deploys a local directory to a Hugging Face Space.

        :param space_id: The ID of the Hugging Face Space (e.g., "harvesthealth/ImmoSpider").
        :param local_path: The local path to the directory to be deployed.
        :param secrets: A JSON string of a dictionary containing the secrets to be set.
        """
        try:
            # 1. Authenticate with Hugging Face.
            # Assumes HF_TOKEN is set in the environment.
            hf_api = HfApi()
            token = os.environ.get("HF_TOKEN")
            if not token:
                return Response(message="Error: HF_TOKEN environment variable not set.", break_loop=True)

            # 2. Set secrets for the space.
            try:
                secrets_dict = json.loads(secrets)
                for key, value in secrets_dict.items():
                    hf_api.add_space_secret(repo_id=space_id, key=key, value=value)
            except json.JSONDecodeError:
                return Response(message="Error: Invalid JSON format for secrets.", break_loop=True)
            except Exception as e:
                return Response(message=f"Error setting secrets: {e}", break_loop=True)

            # 3. Clone, commit, and push the files.
            repo_url = f"https://huggingface.co/spaces/{space_id}"
            repo = Repository(
                local_dir=local_path,
                clone_from=repo_url,
                use_auth_token=token,
                git_user="Agent",
                git_email="agent@huggingface.com",
            )

            # The `huggingface_hub` library handles adding, committing, and pushing.
            # We assume the files are already in the `local_path` directory.
            # The `Repository` class automatically tracks changes.
            repo.push_to_hub(commit_message="Deploy new version from agent.")

            return Response(message=f"Successfully deployed to Hugging Face Space: {space_id}", break_loop=False)

        except Exception as e:
            return Response(message=f"An unexpected error occurred during deployment: {e}", break_loop=True)
