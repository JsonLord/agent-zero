from python.helpers.tool import Tool, Response
import asyncio
import os

class GitGithubRepoSummary(Tool):
    """
    A tool that summarizes a GitHub repository.
    """

    async def execute(self, user: str, repo: str, **kwargs) -> Response:
        """
        A tool that summarizes a GitHub repository.
        Args:
            user: the user of the github repository
            repo: the name of the repository
        Returns:
            summary: a string with a summary of the github repository repo of user
        """

        url = f"https://github.com/{user}/{repo}"
        ingest_path = os.path.expanduser("~/go/bin/ingest")

        # Run the ingest command
        process = await asyncio.create_subprocess_exec(
            ingest_path, "--web", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return Response(message=f"Error summarizing repository: {stderr.decode()}", break_loop=False)

        summary = stdout.decode()

        # Truncate the summary as requested
        truncated_summary = summary[:13904] # 16000 - 2096

        return Response(message=truncated_summary, break_loop=False)
