import unittest
from unittest.mock import patch, MagicMock
import os
import json
import asyncio
from python.tools.jules_api import JulesAPI

class TestJulesAPI(unittest.TestCase):

    @patch.dict(os.environ, {"JULES_API_KEY": "test_api_key"})
    @patch('requests.request')
    def test_list_sources_success(self, mock_request):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"sources": ["source1", "source2"]}'
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        mock_agent = MagicMock()
        mock_agent.agent_name = "test_agent"
        mock_agent.context.log.log.return_value = MagicMock()
        mock_loop_data = MagicMock()

        tool = JulesAPI(
            agent=mock_agent,
            name="jules_api",
            method=None,
            args={"command": "list_sources"},
            message="test_message",
            loop_data=mock_loop_data
        )

        # Act
        response = asyncio.run(tool.execute())

        # Assert
        self.assertEqual(response.message, '{"sources": ["source1", "source2"]}')
        mock_request.assert_called_once_with(
            "GET",
            "https://jules.googleapis.com/v1alpha/sources",
            headers={
                "X-Goog-Api-Key": "test_api_key",
                "Content-Type": "application/json"
            },
            json=None
        )

if __name__ == '__main__':
    unittest.main()
