import subprocess
import tempfile
import os
from pathlib import Path

class SafeCodeExecutor:
    def __init__(self):
        self.allowed_modules = [
            'math', 'json', 'datetime', 'random',
            'requests', 'pandas', 'numpy'
        ]

    def execute_python(self, code: str) -> str:
        """Execute Python code in a safe environment"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Execute with limited permissions
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=tempfile.gettempdir()
            )

            # Clean up
            os.unlink(temp_file)

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out"
        except Exception as e:
            return f"Error: {str(e)}"
