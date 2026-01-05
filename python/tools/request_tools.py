from python.helpers.tool import Tool, Response
import json

class RequestTools(Tool):
    """
    A tool to get a list of all available tools for the current agent.
    """

    async def execute(self, **kwargs) -> Response:
        """
        Returns a JSON formatted list of available tools, including their names and descriptions.
        """
        tools_data = []

        if not hasattr(self.agent, 'tools') or not self.agent.tools:
            return Response(message="No tools found for the current agent.", break_loop=False)

        for tool_instance in self.agent.tools:
            tool_name = tool_instance.name
            # The description is the docstring of the tool's class.
            tool_description = tool_instance.__class__.__doc__.strip() if tool_instance.__class__.__doc__ else "No description available."

            tools_data.append({
                "name": tool_name,
                "description": tool_description
            })

        # Sort tools by name for consistent output
        sorted_tools = sorted(tools_data, key=lambda x: x['name'])

        # Format as a nice JSON string
        response_json = json.dumps(sorted_tools, indent=2)

        return Response(message=response_json, break_loop=False)
