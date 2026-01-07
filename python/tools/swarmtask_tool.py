import subprocess
import json
import tempfile
import os
from python.helpers.tool import Tool, Response

class SwarmtaskTool(Tool):
    """
    A tool to execute tasks in parallel using the swarmtask script.
    """

    async def execute(self, tasks: str, **kwargs) -> Response:
        """
        Executes a set of tasks in parallel and returns a structured JSON response.
        The tasks parameter should be a JSON string representing a dictionary of commands,
        where the keys are task IDs.
        """
        script_path = "scripts/swarmtask/launchswarm.sh"

        try:
            # Ensure the script is executable.
            os.chmod(script_path, 0o755)

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                tmp_file.write(tasks)
                tmp_file_path = tmp_file.name

            result = subprocess.run(
                [script_path, tmp_file_path],
                capture_output=True,
                text=True,
                check=True,
            )

            # The script now returns a JSON object with the results.
            return Response(message=result.stdout, break_loop=False)

        except subprocess.CalledProcessError as e:
            # If the script itself fails, return the error.
            return Response(message=json.dumps({"error": f"Swarmtask script failed: {e.stderr}"}), break_loop=True)
        except FileNotFoundError:
            return Response(message=json.dumps({"error": "Swarmtask script not found."}), break_loop=True)
        except json.JSONDecodeError:
            return Response(message=json.dumps({"error": "Invalid JSON format for tasks."}), break_loop=True)
