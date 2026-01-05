import unittest
from unittest.mock import patch, MagicMock
import asyncio
from python.tools.huggingface_hub_tool import HuggingFaceHubTool

class TestHuggingFaceHubTool(unittest.TestCase):

    def setUp(self):
        self.agent = MagicMock()
        self.tool = HuggingFaceHubTool(self.agent, "huggingface_hub_tool", None, {}, "", None)

    @patch('python.tools.huggingface_hub_tool.HfApi')
    def test_huggingface_hub_tool_success(self, mock_hf_api):
        # Mock the HfApi client and its method
        mock_api_instance = MagicMock()
        mock_api_instance.create_repo.return_value = {"repo_id": "test-repo", "private": False}
        mock_hf_api.return_value = mock_api_instance

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(method_name="create_repo", method_args={"repo_id": "test-repo"}))

        # Assert that the HfApi method was called with the correct arguments
        mock_api_instance.create_repo.assert_called_with(repo_id="test-repo")

        # Assert that the response message contains the serialized result
        self.assertIn('"repo_id": "test-repo"', response.message)

    def test_huggingface_hub_tool_method_not_found(self):
        # Run the tool with a method that doesn't exist
        response = asyncio.run(self.tool.execute(method_name="non_existent_method", method_args={}))

        # Assert the error message for a method not found
        self.assertIn("Error: Method 'non_existent_method' not found on HfApi client.", response.message)

    @patch('python.tools.huggingface_hub_tool.HfApi')
    def test_huggingface_hub_tool_api_exception(self, mock_hf_api):
        # Mock the HfApi to raise an exception
        mock_api_instance = MagicMock()
        mock_api_instance.create_repo.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api_instance

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(method_name="create_repo", method_args={"repo_id": "test-repo"}))

        # Assert the error message for an API exception
        self.assertIn("An error occurred while calling 'create_repo': API Error", response.message)

if __name__ == '__main__':
    unittest.main()
