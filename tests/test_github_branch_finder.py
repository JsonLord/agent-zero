import unittest
from unittest.mock import patch, MagicMock
import asyncio
import requests
from python.tools.github_branch_finder import GitHubBranchFinder

class TestGitHubBranchFinder(unittest.TestCase):

    def setUp(self):
        self.agent = MagicMock()
        self.tool = GitHubBranchFinder(self.agent, "github_branch_finder", None, {}, "", None)

    @patch('requests.get')
    def test_github_branch_finder_success(self, mock_get):
        # Mock the response from requests.get for branches
        mock_branches_response = MagicMock()
        mock_branches_response.status_code = 200
        mock_branches_response.json.return_value = [
            {
                "name": "main",
                "commit": {
                    "sha": "c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc",
                    "url": "https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc"
                }
            },
            {
                "name": "develop",
                "commit": {
                    "sha": "c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbd",
                    "url": "https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbd"
                }
            }
        ]

        # Mock the response from requests.get for commits
        mock_main_commit_response = MagicMock()
        mock_main_commit_response.status_code = 200
        mock_main_commit_response.json.return_value = {
            "commit": {
                "committer": {
                    "date": "2023-01-01T12:00:00Z"
                }
            }
        }

        mock_develop_commit_response = MagicMock()
        mock_develop_commit_response.status_code = 200
        mock_develop_commit_response.json.return_value = {
            "commit": {
                "committer": {
                    "date": "2023-01-02T12:00:00Z"
                }
            }
        }

        mock_get.side_effect = [
            mock_branches_response,
            mock_main_commit_response,
            mock_develop_commit_response,
        ]

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(repo_name="octocat/Hello-World"))

        # Assert that the response message is formatted correctly
        expected_output = (
            "Branches for octocat/Hello-World:\n"
            "- develop (Last commit: 2023-01-02 12:00:00) **(Latest)**\n"
            "- main (Last commit: 2023-01-01 12:00:00)\n"
        )
        self.assertEqual(response.message, expected_output)

    @patch('requests.get')
    def test_github_branch_finder_not_found(self, mock_get):
        # Mock a 404 Not Found error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found for url")
        mock_get.return_value = mock_response

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(repo_name="nonexistent/repo"))

        # Assert the error message
        self.assertIn("Error fetching branches for nonexistent/repo", response.message)

if __name__ == '__main__':
    unittest.main()
