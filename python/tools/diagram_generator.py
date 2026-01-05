import subprocess
from python.helpers.tool import Tool, Response

class DiagramGenerator(Tool):
    """
    A tool to generate diagrams from mermaid syntax.
    """

    async def execute(self, mermaid_syntax: str, output_path: str = "tmp/diagram.svg", **kwargs) -> Response:
        """
        Generates a diagram from mermaid syntax and saves it to a file.
        """
        try:
            # The mmdc command is installed globally via npm in the Dockerfile
            result = subprocess.run(
                ["mmdc", "-i", "-", "-o", output_path],
                input=mermaid_syntax,
                capture_output=True,
                text=True,
                check=True,
            )
            return Response(message=f"Diagram successfully generated at {output_path}", break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f"Error generating diagram: {e.stderr}", break_loop=False)
        except FileNotFoundError:
            return Response(message="Error: mmdc command not found. Please ensure @mermaid-js/mermaid-cli is installed globally.", break_loop=False)
