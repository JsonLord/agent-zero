import subprocess
from python.helpers.tool import Tool, Response

class TaskmasterTool(Tool):
    """
    A tool to interact with the todo.ai command-line tool.
    """

    async def execute(self, command: str, **kwargs) -> Response:
        """
        Executes a command for the todo.ai tool.
        """
        try:
            # The todo.ai script is installed in the Docker environment and should be in the PATH
            result = subprocess.run(
                ["todo.ai"] + command.split(),
                capture_output=True,
                text=True,
                check=True,
            )
            return Response(message=result.stdout, break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f"Error executing command: {e.stderr}", break_loop=False)
        except FileNotFoundError:
            return Response(message="Error: todo.ai script not found. Please ensure it is installed and in the system's PATH.", break_loop=False)
