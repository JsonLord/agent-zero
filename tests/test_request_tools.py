import unittest
from unittest.mock import MagicMock
import asyncio
import json
from python.tools.request_tools import RequestTools

class TestRequestTools(unittest.TestCase):

    def setUp(self):
        # Mock the agent and its tools attribute
        self.agent = MagicMock()

        # Create mock tools with names and docstrings
        mock_tool_1 = MagicMock()
        mock_tool_1.name = "tool_a"
        mock_tool_1.__class__.__doc__ = "Description for Tool A."

        mock_tool_2 = MagicMock()
        mock_tool_2.name = "tool_b"
        mock_tool_2.__class__.__doc__ = "Description for Tool B."

        self.agent.tools = [mock_tool_1, mock_tool_2]

        # Instantiate the tool with the mocked agent
        self.tool = RequestTools(self.agent, "request_tools", None, {}, "", None)

    def test_request_tools_success(self):
        # Run the tool's execute method
        response = asyncio.run(self.tool.execute())

        # Expected output is a sorted JSON list of tools
        expected_tools = [
            {"name": "tool_a", "description": "Description for Tool A."},
            {"name": "tool_b", "description": "Description for Tool B."}
        ]
        expected_json = json.dumps(expected_tools, indent=2)

        # Assert that the response message is the expected JSON string
        self.assertEqual(response.message, expected_json)

    def test_request_tools_no_tools_found(self):
        # Configure the agent to have no tools
        self.agent.tools = []

        # Run the tool's execute method
        response = asyncio.run(self.tool.execute())

        # Assert the response message for when no tools are found
        self.assertEqual(response.message, "No tools found for the current agent.")

if __name__ == '__main__':
    unittest.main()
