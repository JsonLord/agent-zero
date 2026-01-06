import datetime
from python.helpers.tool import Tool, Response
from python.helpers.files import write_file

class DevelopWorkflow(Tool):
    """
    A tool to orchestrate the initial "Develop" workflow.
    """

    async def execute(self, project_name: str, research_topic: str, research_depth: str = "shallow", **kwargs) -> Response:
        """
        Orchestrates the initial "Develop" workflow:
        1. Logs the start of an ideation session.
        2. Delegates research tasks to the research-agent.
        3. Presents the research findings to the user and prompts for feedback.
        """
        # 1. Log the start of an ideation session
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file_path = f"/app/ideate/{project_name}_{timestamp}.md"
        log_content = f"# Ideation Session for {project_name} at {timestamp}\n\n"
        write_file(log_file_path, log_content)

        # 2. Delegate research tasks to the research-agent
        research_task = f"Research the following topic: {research_topic}"
        research_response = await self.agent.call_subordinate(
            "research-agent",
            task=research_task,
            depth=research_depth,
        )

        # 3. Present the research findings to the user and prompts for feedback
        message = f"## Research Findings for {research_topic}\n\n"
        message += research_response.message
        message += "\n\nPlease review the research and provide your feedback."

        return Response(message=message, break_loop=False)
