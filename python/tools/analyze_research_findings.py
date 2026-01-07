from python.helpers.tool import Tool, Response

class AnalyzeResearchFindings(Tool):
    """
    A tool to analyze research findings and provide recommendations.
    """

    async def execute(self, findings: str, **kwargs) -> Response:
        """
        Analyzes research findings and provides recommendations.
        """
        prompt = f"""
Analyze the following research findings and provide a structured recommendation. The output should be a markdown-formatted report with the following sections:

**1. Summary of Findings:**
Briefly summarize the key takeaways from the research.

**2. Relevance to the Project:**
Assess how relevant the findings are to the current project goals.

**3. Implementation Strategy:**
Propose a concrete strategy for how to implement or integrate the findings. Include potential challenges and how to mitigate them.

**4. Recommendation:**
Provide a clear "Go" or "No-Go" recommendation on whether to proceed with the implementation.

**Research Findings:**
{findings}
"""
        analysis = await self.agent.llm.chat(prompt)
        return Response(message=analysis, break_loop=False)
