from python.helpers.tool import Tool, Response
import re

class GitOrJulesDecision(Tool):
    """
    A tool to decide whether to use git-agent or jules-agent for a task.
    """

    async def execute(self, task_description: str, **kwargs) -> Response:
        """
        Analyzes a task description to recommend either git-agent or jules-agent.
        """
        # A simple heuristic: if the task description mentions more than one file path,
        # or uses words like "refactor", "implement", "complex", or "multiple",
        # recommend jules-agent. Otherwise, recommend git-agent.

        file_path_mentions = len(re.findall(r'(\s|^)[\/\w\.-]+(\s|$)', task_description))
        complex_words = ["refactor", "implement", "complex", "multiple", "integrate", "add", "create"]

        if file_path_mentions > 1 or any(word in task_description.lower() for word in complex_words):
            recommendation = "jules-agent"
            reason = "The task appears to involve multiple files or complex changes."
        else:
            recommendation = "git-agent"
            reason = "The task appears to be a simple, single-file change."

        return Response(message=f"Recommendation: {recommendation}\nReason: {reason}", break_loop=False)
