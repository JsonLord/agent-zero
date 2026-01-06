import subprocess
import tempfile
import shutil
from python.helpers.tool import Tool, Response

class DiagramTool(Tool):
    """
    A tool to generate diagrams from Mermaid syntax.
    """

    async def execute(self, mermaid_syntax: str, **kwargs) -> Response:
        """
        Generates a diagram from Mermaid syntax and returns the SVG content.
        """
        if not self.is_mmdc_installed():
            return Response(message="Error: The Mermaid CLI (mmdc) is not installed. Please install it by running 'npm install -g @mermaid-js/mermaid-cli'.", break_loop=True)

        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mmd') as tmp_file:
                tmp_file.write(mermaid_syntax)
                tmp_file_path = tmp_file.name

            output_file_path = tmp_file_path.replace('.mmd', '.svg')

            subprocess.run(
                ['mmdc', '-i', tmp_file_path, '-o', output_file_path],
                check=True,
                capture_output=True,
                text=True
            )

            with open(output_file_path, 'r') as f:
                svg_content = f.read()

            return Response(message=svg_content, break_loop=False)
        except subprocess.CalledProcessError as e:
            return Response(message=f'Error generating diagram: {e.stderr}', break_loop=False)
        except Exception as e:
            return Response(message=f'An unexpected error occurred: {str(e)}', break_loop=False)

    def is_mmdc_installed(self):
        """
        Checks if the mmdc command is available.
        """
        return shutil.which('mmdc') is not None
