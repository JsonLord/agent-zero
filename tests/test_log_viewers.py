import unittest
from unittest.mock import MagicMock, patch

from python.tools.huggingface_log_viewer import HuggingfaceLogViewer
from agent import Agent

class TestHuggingfaceLogViewer(unittest.TestCase):

    @patch('python.tools.huggingface_log_viewer.requests.get')
    def test_execute(self, mock_requests_get):
        # Arrange
        mock_agent = Agent(number=0, config=MagicMock())

        # Mock for the log stream response
        mock_log_response = MagicMock()
        mock_log_response.status_code = 200
        mock_log_response.text = "2024-01-01T12:00:00Z: Log message 1\n2024-01-01T12:00:01Z: Log message 2"
        mock_requests_get.return_value = mock_log_response

        tool = HuggingfaceLogViewer(mock_agent, name="huggingface_log_viewer", method=MagicMock(), args=MagicMock(), message=MagicMock(), loop_data=MagicMock())

        # Act
        import asyncio
        result = asyncio.run(tool.execute(repo_id="test/space"))

        # Assert
        self.assertIn("2024-01-01T12:00:00Z: Log message 1", result.message)
        self.assertIn("2024-01-01T12:00:01Z: Log message 2", result.message)


from python.tools.jules_log_viewer import JulesLogViewer

class TestJulesLogViewer(unittest.TestCase):

    def test_list_sessions(self):
        # Arrange
        mock_agent = Agent(number=0, config=MagicMock())
        mock_jules_api_tool = unittest.mock.AsyncMock()
        mock_agent.get_tool = MagicMock(return_value=mock_jules_api_tool)

        tool = JulesLogViewer(mock_agent, method=MagicMock(), args=MagicMock(), message=MagicMock(), loop_data=MagicMock())

        # Act
        import asyncio
        asyncio.run(tool.list_sessions(pageSize=10))

        # Assert
        mock_jules_api_tool.execute.assert_called_with(command="list_sessions", pageSize=10)

    def test_list_activities(self):
        # Arrange
        mock_agent = Agent(number=0, config=MagicMock())
        mock_jules_api_tool = unittest.mock.AsyncMock()
        mock_agent.get_tool = MagicMock(return_value=mock_jules_api_tool)

        tool = JulesLogViewer(mock_agent, method=MagicMock(), args=MagicMock(), message=MagicMock(), loop_data=MagicMock())

        # Act
        import asyncio
        asyncio.run(tool.list_activities(session_id="test_session", pageSize=20))

        # Assert
        mock_jules_api_tool.execute.assert_called_with(command="list_activities", session_id="test_session", pageSize=20)
