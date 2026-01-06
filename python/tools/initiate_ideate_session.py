from python.helpers.tool import Tool, Response

class InitiateIdeateSession(Tool):
    """
    A tool to initiate the "Develop" workflow.
    """

    async def execute(self, project_name: str, research_topic: str, research_depth: str = "shallow", **kwargs) -> Response:
        """
        Initiates the "Develop" workflow by calling the develop_workflow tool.
        """
        return await self.agent.call_tool(
            "develop_workflow",
            project_name=project_name,
            research_topic=research_topic,
            research_depth=research_depth,
        )
