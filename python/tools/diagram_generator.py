import subprocess
import shutil
import os
from python.helpers.tool import Tool, Response

class DiagramGenerator(Tool):
    """
    A tool to generate diagrams from mermaid syntax.
    It uses npx to run the mermaid-cli without a global installation.
    """

    async def execute(self, mermaid_syntax: str, output_path: str = "tmp/diagram.svg", **kwargs) -> Response:
        """
        Generates a diagram from mermaid syntax and saves it to a file.
        """
        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Execute mmdc using npx
            result = subprocess.run(
                ["npx", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", "-", "-o", output_path],
                input=mermaid_syntax,
                capture_output=True,
                text=True,
                check=True,
            )
            return Response(message=f"Diagram successfully generated at {output_path}", break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f"Error generating diagram: {e.stderr}", break_loop=False)
        except FileNotFoundError:
            return Response(message="Error: npx command not found. Please ensure Node.js and npm are installed.", break_loop=False)
