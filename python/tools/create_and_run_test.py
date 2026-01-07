import json
import subprocess
import tempfile
from python.helpers.tool import Tool, Response

class CreateAndRunTest(Tool):
    """
    A dedicated tool for the developer-agent to create and run a test for a given goal.
    """

    async def execute(self, test_goal: str, **kwargs) -> Response:
        """
        Creates and runs a test for a given goal and returns a structured JSON response.
        """
        # 1. Use the LLM to generate a test script.
        prompt = f"""
Based on the following test goal, generate a Python script that uses the pytest framework to verify the goal. The script should be self-contained and print 'SUCCESS' if the test passes and 'FAILURE' followed by the reason if it fails.

Test Goal: {test_goal}
"""
        test_script_code = await self.agent.llm.chat(prompt)

        # 2. Execute the generated test script.
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as tmp_file:
                tmp_file.write(test_script_code)
                tmp_file_path = tmp_file.name

            result = subprocess.run(
                ['python', tmp_file_path],
                capture_output=True,
                text=True,
                check=True
            )

            # 3. Parse the output and return a structured response.
            if 'SUCCESS' in result.stdout:
                response_data = {"status": "success", "message": result.stdout}
            else:
                response_data = {"status": "failure", "message": result.stdout or result.stderr}

        except subprocess.CalledProcessError as e:
            response_data = {"status": "failure", "message": e.stderr}
        except Exception as e:
            response_data = {"status": "failure", "message": str(e)}

        return Response(message=json.dumps(response_data), break_loop=False)
