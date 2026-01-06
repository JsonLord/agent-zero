from python.helpers.tool import Tool

class JulesLogViewer(Tool):
    """
    A tool for viewing logs and activities from the Jules API.
    """

    def __init__(self, agent, **kwargs):
        super().__init__(agent, "jules_log_viewer", **kwargs)
        # It's assumed that a 'jules_api' tool is available to the agent.
        # This tool acts as a wrapper around the existing jules_api tool.
        self.jules_api_tool = self.agent.get_tool("jules_api")

    async def list_sessions(self, pageSize: int = 5, **kwargs):
        """
        Lists all available Jules sessions.
        """
        if not self.jules_api_tool:
            return "Error: The 'jules_api' tool is not available."

        return await self.jules_api_tool.execute(command="list_sessions", pageSize=pageSize, **kwargs)

    async def list_activities(self, session_id: str, pageSize: int = 30, **kwargs):
        """
        Lists all activities for a specific Jules session.
        This is the primary way to get logs and work updates for a session.
        """
        if not self.jules_api_tool:
            return "Error: The 'jules_api' tool is not available."

        return await self.jules_api_tool.execute(command="list_activities", session_id=session_id, pageSize=pageSize, **kwargs)
