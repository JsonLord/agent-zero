from python.helpers.tool import Tool, Response

class PostIdeationWorkflow(Tool):
    """
    A tool to handle the post-ideation workflow, including log analysis, research, and feasibility evaluation.
    """

    async def execute(self, log_file: str, github_repo: str, session_timestamp: str, **kwargs) -> Response:
        """
        Executes the post-ideation workflow.
        """
        # Create a unique filename for the log upload.
        project_name = log_file.split('/')[-2].split('_')[0]
        destination_path = f"log_{project_name}_{session_timestamp}.md"

        # 1. Upload the log file to GitHub
        await self.agent.call_tool(
            "upload_file_to_github",
            repo=github_repo,
            branch="logs",
            filepath=log_file,
            destination_path=destination_path
        )

        # 2. Analyze the log script and make notes
        log_content = await self.agent.call_tool("read_file", filepath=log_file)
        analysis = await self.agent.llm.chat(
            f"Analyze the following ideation session log and extract components, questions, and research candidates:\n\n{log_content}"
        )

        # 3. Trigger the research agent
        research_candidates = await self.agent.llm.chat(
            f"Extract a comma-separated list of research candidates from the following analysis:\n\n{analysis}"
        )
        research_findings = await self.agent.call_tool(
            "research-agent",
            query=research_candidates,
            depth="deep"
        )

        # 4. Have git-agent and huggingface-agent analyze the findings
        git_analysis = await self.agent.call_tool(
            "analyze_research_findings",
            findings=research_findings
        )
        hf_analysis = await self.agent.call_tool(
            "analyze_research_findings",
            findings=research_findings
        )

        # 5. Present the final recommendations to the user
        recommendations = f"**Git Agent Recommendations:**\n{git_analysis}\n\n**Hugging Face Agent Recommendations:**\n{hf_analysis}"
        return Response(message=recommendations, break_loop=False)
