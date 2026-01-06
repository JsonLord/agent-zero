import subprocess
import json
import tempfile
from python.helpers.tool import Tool, Response

class SwarmtaskTool(Tool):
    """
    A tool to execute tasks in parallel using the swarmtask script.
    """

    async def execute(self, tasks: str, **kwargs) -> Response:
        """
        Executes a set of tasks in parallel.
        The tasks parameter should be a JSON string representing a list of commands.
        """
        try:
            # The swarmtask script should be located in the scripts directory
            # and made executable.
            script_path = "scripts/swarmtask/launchswarm.sh"

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                tmp_file.write(tasks)
                tmp_file_path = tmp_file.name

            result = subprocess.run(
                [script_path, tmp_file_path],
                capture_output=True,
                text=True,
                check=True,
            )
            return Response(message=result.stdout, break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f"Error executing swarmtask: {e.stderr}", break_loop=False)
        except FileNotFoundError:
            return Response(message="Error: swarmtask script not found. Please ensure it is located at scripts/swarmtask/launchswarm.sh and is executable.", break_loop=False)
        except json.JSONDecodeError:
            return Response(message="Error: Invalid JSON format for tasks.", break_loop=False)
