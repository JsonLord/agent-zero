from python.helpers.tool import Tool, Response

class ConcludeIdeateSession(Tool):
    """
    A tool to conclude an ideation session and trigger the post-ideation workflow.
    """

    async def execute(self, log_file: str, github_repo: str = "JsonLord/agent-notes", **kwargs) -> Response:
        """
        Concludes an ideation session and triggers the post-ideation workflow.
        """
        self.agent.log_file = None  # Clear the log file from the agent's state

        return await self.agent.call_tool(
            "post_ideation_workflow",
            log_file=log_file,
            github_repo=github_repo,
        )
