import os
import datetime
from python.helpers.tool import Tool, Response

class InitiateIdeateSession(Tool):
    """
    A tool to initiate an "ideation" session for a new project.
    This creates a dedicated log file for the session.
    """

    async def execute(self, project_name: str, **kwargs) -> Response:
        """
        Initializes an ideation session by creating a unique directory and
        log file for the conversation.

        Args:
            project_name: The name of the project to be developed.
        """
        # Sanitize project_name to be used in a directory path
        sanitized_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '_')).rstrip()
        sanitized_project_name = sanitized_project_name.replace(' ', '_')

        # Create a unique session identifier
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join("/app", "ideate", f"{sanitized_project_name}_{session_id}")

        try:
            os.makedirs(session_dir, exist_ok=True)
            log_file_path = os.path.join(session_dir, "session_log.md")

            # Store the log file path in the agent's loop_data for the main loop to access
            self.agent.loop_data['ideation_log_path'] = log_file_path

            # Create an empty file to mark the beginning
            with open(log_file_path, 'w') as f:
                f.write(f"# Ideation Session: {project_name}\n")
                f.write(f"Session Start: {datetime.datetime.now()}\n\n")

            return Response(
                message=f"Ideation session for '{project_name}' has started. All messages will be logged to {log_file_path}. Use the 'end_ideate_session' tool to conclude.",
                break_loop=False
            )
        except Exception as e:
            return Response(
                message=f"Error starting ideation session: {e}",
                break_loop=False
            )
