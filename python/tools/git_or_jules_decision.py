import re
import json
from python.helpers.tool import Tool, Response

class GitOrJulesDecision(Tool):
    """
    A tool to decide whether to use git-agent or jules-agent for a task and delegate accordingly.
    """

    async def execute(self, task_description: str, sub_agent_instructions: str, **kwargs) -> Response:
        """
        Analyzes a task description, chooses between git-agent and jules-agent,
        and delegates the task to the chosen agent.

        :param task_description: A description of the task to be performed.
        :param sub_agent_instructions: A JSON string of arguments to be passed to the sub-agent.
        """
        # Heuristic: Count file paths and look for complex words.
        # The regex looks for file-like paths.
        file_path_mentions = len(re.findall(r'[\w\/-]+\.[\w\/-]+', task_description))
        complex_words = ["refactor", "implement", "complex", "multiple", "integrate", "add", "create", "component"]

        # Decision logic based on the requirements.
        if file_path_mentions >= 3 or any(word in task_description.lower() for word in complex_words):
            chosen_agent = "jules-agent"
        else:
            chosen_agent = "git-agent"

        try:
            # Parse the instructions for the sub-agent.
            agent_args = json.loads(sub_agent_instructions)
        except json.JSONDecodeError:
            return Response(message="Error: Invalid JSON format for sub_agent_instructions.", break_loop=True)

        # Delegate the task to the chosen agent.
        response = await self.agent.call_tool(chosen_agent, **agent_args)
        return response
