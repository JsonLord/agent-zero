from python.helpers.tool import Tool

class KeywordPersonas(Tool):
    """
    An extension to prepend a persona prompt to the user's message based on keywords.
    """

    async def execute(self, message: str, **kwargs) -> str:
        """
        Inspects the user's message for keywords and prepends the appropriate persona prompt.
        """
        if message.lower().startswith("develop"):
            persona_prompt = """
You are in 'Develop' mode. Your goal is to conduct an ideation session, including calling the research agent, investigating git directories, finding suitable solutions, and critically reflecting on ideas. The entire session will be logged to a file in the /app directory. Once the session is complete, the following will be kicked off automatically:
1. The log file will be uploaded to github JsonLord/agent-notes/logs.
2. The developer agent will analyze the log script and make notes, questions, and annotations.
3. The research agent will be given a list of notes to find possible huggingface space or github code replacements.
4. The git-agent and huggingface agent will analyze the findings and provide recommendations.
"""
        elif message.lower().startswith("deploy"):
            persona_prompt = """
You are in 'Deploy' mode. Your goal is to deploy an app on a new huggingface space. You will:
1. Create a new space with the sdk.
2. Determine if it is a custom or github app.
3. For github apps, create a dockerfile to clone the repo.
4. For custom apps, use the Plan function to plan the project.
5. After deployment, use the monitor agent to retrieve logs and fix any issues.
6. Test the app and any API endpoints.
7. Inform the user of the result.
"""
        elif message.lower().startswith("plan"):
            persona_prompt = """
You are in 'Plan' mode. Your goal is to create a project plan. You will:
1. Plan the project's scope and decide whether to write files or use the jules-agent.
2. Generate a question sheet for the user to resolve ambiguities.
3. Reflect on the user's answers and rework the plan.
4. Generate a final plan file, including a Mermaid diagram.
"""
        elif message.lower().startswith("run"):
            persona_prompt = """
You are in 'Run' mode. Your goal is to clone a repository, understand how to run it, and test its use cases. You will:
1. Use the `git-agent` to clone the repository.
2. Ask the `git-agent` how to build and run the code.
3. Investigate the code to identify its main use cases.
4. Run and test the identified use cases.
5. Present a summary of the successful use cases and, if any tests failed, ask the user if they should be fixed before engaging the 'Adapt' workflow.
"""
        elif message.lower().startswith("adapt"):
            persona_prompt = """
You are in 'Adapt' mode. Your goal is to make changes to an existing codebase. You will:
1. Use the 'Plan' workflow to analyze the codebase and create a structured plan for the required changes.
2. Once the plan is clear, use the appropriate sub-agent (`git-agent` for small changes, `jules-agent` for large ones) to implement the changes.
3. Re-test the affected use cases to ensure the changes were successful and did not introduce regressions.
"""
        else:
            return message

        return f"{persona_prompt}\n\n{message}"
