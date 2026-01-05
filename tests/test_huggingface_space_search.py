import unittest
from unittest.mock import patch, MagicMock
import json
import asyncio
from python.tools.huggingface_space_search import SearchHFSpaces

class TestSearchHFSpaces(unittest.TestCase):

    def setUp(self):
        self.agent = MagicMock()
        self.tool = SearchHFSpaces(self.agent, "search_hf_spaces", None, {}, "", None)

    @patch('requests.get')
    def test_search_hf_spaces_success(self, mock_get):
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "space1", "likes": 10, "tags": ["gradio", "research"]},
            {"id": "space2", "likes": 20, "tags": ["gradio", "ai"]}
        ]
        mock_get.return_value = mock_response

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(search_terms="gradio"))

        # Assert that the response message is a JSON string of the spaces
        self.assertEqual(json.loads(response.message), [
            {"id": "space2", "likes": 20, "tags": ["gradio", "ai"]},
            {"id": "space1", "likes": 10, "tags": ["gradio", "research"]}
        ])

    @patch('requests.get')
    def test_search_hf_spaces_api_error(self, mock_get):
        # Mock an API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(search_terms="error"))

        # Assert the error message
        self.assertIn("Error searching for 'error': 500", response.message)

    @patch('requests.get')
    def test_search_hf_spaces_exception(self, mock_get):
        # Mock an exception during the request
        mock_get.side_effect = Exception("Test exception")

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute(search_terms="exception"))

        # Assert the exception message
        self.assertIn("Exception searching for 'exception': Test exception", response.message)

if __name__ == '__main__':
    unittest.main()
