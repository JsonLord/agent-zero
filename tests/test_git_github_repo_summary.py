import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from python.tools.git_github_repo_summary import GitGithubRepoSummary

class TestGitGithubRepoSummary(unittest.TestCase):

    def setUp(self):
        self.agent = MagicMock()
        self.tool = GitGithubRepoSummary(self.agent, "git_repo_summary", None, {}, "", None)

    @patch('asyncio.create_subprocess_exec')
    def test_git_github_repo_summary_success(self, mock_create_subprocess_exec):
        # Mock the subprocess to return a successful execution
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"This is a summary.", b"")
        mock_process.returncode = 0
        mock_create_subprocess_exec.return_value = mock_process

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(user="testuser", repo="testrepo"))

        # Assert that the ingest command was called correctly
        expected_command = "ingest"
        mock_create_subprocess_exec.assert_called_with(
            unittest.mock.ANY, "--web", "https://github.com/testuser/testrepo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Assert that the response message is the summary
        self.assertEqual(response.message, "This is a summary.")

    @patch('asyncio.create_subprocess_exec')
    def test_git_github_repo_summary_error(self, mock_create_subprocess_exec):
        # Mock the subprocess to return an error
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_create_subprocess_exec.return_value = mock_process

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(user="testuser", repo="testrepo"))

        # Assert that the response message contains the error
        self.assertIn("Error summarizing repository: Error message", response.message)

if __name__ == '__main__':
    unittest.main()
