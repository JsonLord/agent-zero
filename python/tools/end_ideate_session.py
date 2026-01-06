import os
import datetime
from python.helpers.tool import Tool, Response

class EndIdeateSession(Tool):
    """
    A tool to conclude an "ideation" session and upload the log to GitHub.
    """

    async def execute(self, **kwargs) -> Response:
        """
        Finalizes an ideation session by uploading the session log to a
        specified GitHub repository and then clears the session state.
        """
        if 'ideation_log_path' not in self.agent.loop_data or not self.agent.loop_data['ideation_log_path']:
            return Response(
                message="Error: No active ideation session found.",
                break_loop=False
            )

        log_file_path = self.agent.loop_data['ideation_log_path']

        # 1. Finalize the log file
        with open(log_file_path, 'a') as f:
            f.write(f"\n---\nSession End: {datetime.datetime.now()}\n")

        # 2. Upload the log to GitHub using the git-agent
        try:
            repo_name = self.agent.config.ideation_repo
            repo_path = "logs"
            branch_name = f"ideation-log-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            commit_message = f"docs: Add ideation log for {os.path.basename(os.path.dirname(log_file_path))}"

            # Create a new branch by calling the git-agent tool
            await self.agent.call_tool(
                "git-agent",
                command=f"create_branch --repo {repo_name} --branch {branch_name} --from main"
            )

            # Read the content of the log file to pass to the git-agent
            with open(log_file_path, 'r') as f:
                log_content = f.read()

            # Upload the file to the new branch
            await self.agent.call_tool(
                "git-agent",
                command="upload_file",
                repo=repo_name,
                branch=branch_name,
                path=f"{repo_path}/{os.path.basename(log_file_path)}",
                content=log_content,
                commit_message=commit_message,
            )

            upload_message = f"Ideation log successfully uploaded to {repo_name} on branch {branch_name}."
        except Exception as e:
            upload_message = f"Warning: Failed to upload ideation log to GitHub. You can find the log at {log_file_path}. Error: {e}"

        # 3. Clear the session state
        self.agent.loop_data['ideation_log_path'] = None

        return Response(
            message=f"Ideation session has ended. {upload_message}",
            break_loop=False
        )
