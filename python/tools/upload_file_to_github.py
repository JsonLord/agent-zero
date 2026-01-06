import subprocess
import base64
from python.helpers.tool import Tool, Response

class UploadFileToGithub(Tool):
    """
    A tool to upload a file to a GitHub repository.
    """
    async def execute(self, repo: str, branch: str, filepath: str, destination_path: str, **kwargs) -> Response:
        """
        Uploads a file to a GitHub repository.
        """
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            content_base64 = base64.b64encode(content).decode("utf-8")

            commit_message = f"Upload {destination_path}"

            command = [
                "gh", "api",
                "--method", "PUT",
                f"/repos/{repo}/contents/{destination_path}",
                "-f", f"message={commit_message}",
                "-f", f"content={content_base64}",
                "-f", f"branch={branch}"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return Response(message=f"File uploaded successfully: {result.stdout}", break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f"Error uploading file: {e.stderr}", break_loop=True)
        except FileNotFoundError:
            return Response(message="Error: `gh` CLI not found. Please ensure it is installed and authenticated.", break_loop=True)
        except Exception as e:
            return Response(message=f"An unexpected error occurred: {str(e)}", break_loop=True)
