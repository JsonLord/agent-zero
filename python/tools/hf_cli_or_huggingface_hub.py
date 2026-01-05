from python.helpers.tool import Tool, Response
import json

class HuggingFaceDecisionTool(Tool):
    """
    A tool to decide whether to use the Hugging Face CLI or the huggingface_hub client for a given task.
    """

    async def execute(self, task_description: str, **kwargs) -> Response:
        """
        Analyzes a task description and recommends the best tool to use.

        Args:
            task_description (str): A description of the task to be performed.
        """
        task_description = task_description.lower()

        # Keywords for CLI-based tools
        cli_keywords = ["login", "log in", "logout", "whoami", "scan", "lfs-enable-largefiles", "lfs-track", "delete-cache"]

        # Keywords for Hub client methods (HfApi)
        hub_client_keywords = [
            "create_repo", "delete_repo", "upload_file", "delete_file", "download_file", "list_files",
            "get_full_repo_name", "repo_info", "list_models", "list_datasets", "move_repo",
            "create_branch", "delete_branch", "upload_folder", "create_tag", "delete_tag",
            "create a new public repository"
        ]

        use_cli = any(keyword in task_description for keyword in cli_keywords)
        use_hub_client = any(keyword in task_description for keyword in hub_client_keywords)

        if use_cli:
            recommendation = {
                "tool_to_use": "huggingface-cli",
                "reason": "The task appears to be related to authentication, local environment configuration, or cache management, which are best handled by the CLI.",
                "example_command": "huggingface-cli login"
            }
        elif use_hub_client:
            recommendation = {
                "tool_to_use": "huggingface_hub_tool",
                "reason": "The task involves repository or file management on the Hub, which is efficiently handled by the huggingface_hub client.",
                "example_parameters": {
                    "method_name": "create_repo",
                    "method_args": {"repo_id": "your-repo-id", "private": False}
                }
            }
        elif "download" in task_description:
             recommendation = {
                "tool_to_use": "huggingface_hub_tool",
                "reason": "The task involves downloading files which is best handled by the huggingface_hub client.",
                "example_parameters": {
                    "method_name": "hf_hub_download",
                    "method_args": {"repo_id": "google/pegasus-xsum", "filename": "config.json"}
                }
            }
        else:
            # Default or ambiguous cases
            recommendation = {
                "tool_to_use": "undetermined",
                "reason": "The task description is ambiguous. Please provide more specific keywords. For repository and file operations, use the 'huggingface_hub_tool'. For authentication and local configuration, use the 'huggingface-cli'.",
                "available_tools": ["huggingface-cli", "huggingface_hub_tool"]
            }

        return Response(message=json.dumps(recommendation, indent=2), break_loop=False)
