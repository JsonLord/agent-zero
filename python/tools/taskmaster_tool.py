import subprocess
import os

def taskmaster_tool(command: str) -> str:
    """
    A tool for interacting with the todo.ai task management system.

    Args:
        command: The command to pass to the todo.bash script (e.g., "add 'My new task'", "list").

    Returns:
        The output from the todo.bash script.
    """
    script_path = os.path.join("scripts", "todo.ai", "todo.bash")

    if not os.path.exists(script_path):
        return f"Error: The script was not found at {script_path}. Please ensure the 'todo.ai' repository is cloned in the 'scripts' directory."

    try:
        result = subprocess.run(
            [script_path] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing taskmaster tool: {e}\n{e.stderr}"
    except FileNotFoundError:
        return f"Error: The script at {script_path} could not be executed. Please ensure it has the correct permissions."
