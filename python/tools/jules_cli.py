from python.helpers.tool import Tool, Response

class JulesCLI(Tool):
    """
    A tool for interacting with the Jules CLI.
    """

    async def execute(self, **kwargs):
        """
        Executes a jules command.
        """
        command = self.args.get("command", "")
        if not command:
            return Response(message="Error: No command provided to jules_cli tool.", break_loop=False)

        # We will use the code_execution_tool to run the command in the terminal.
        # This is better than running it directly, because the code_execution_tool
        # already handles interactive sessions, output streaming, and error handling.
        code_execution_tool = self.agent.get_tool(
            name="code_execution",
            method=None,
            args={"runtime": "terminal", "code": f"jules {command}"},
            message=self.message, # pass the original message
            loop_data=self.loop_data,
        )

        # The code_execution_tool has an `execute` method which is the main entry point.
        # It then calls the appropriate method based on the runtime.
        # In our case, it will call `execute_terminal_command`.
        # I'll just call the main `execute` method and let it handle the routing.
        response = await code_execution_tool.execute()

        # The response from the code_execution_tool is a Response object.
        # I'll just return it as is.
        return response
