import unittest
from unittest.mock import MagicMock
import asyncio
import json
from python.tools.hf_cli_or_huggingface_hub import HuggingFaceDecisionTool

class TestHuggingFaceDecisionTool(unittest.TestCase):

    def setUp(self):
        self.agent = MagicMock()
        self.tool = HuggingFaceDecisionTool(self.agent, "hf_decision_tool", None, {}, "", None)

    def test_decision_tool_recommends_cli_for_login(self):
        # Test case for a task description that should use the CLI
        task_description = "I need to log in to my Hugging Face account."
        response = asyncio.run(self.tool.execute(task_description=task_description))

        recommendation = json.loads(response.message)
        self.assertEqual(recommendation["tool_to_use"], "huggingface-cli")
        self.assertIn("authentication", recommendation["reason"])

    def test_decision_tool_recommends_hub_client_for_repo_creation(self):
        # Test case for a task that should use the hub client
        task_description = "Create a new public repository named 'my-awesome-model'."
        response = asyncio.run(self.tool.execute(task_description=task_description))

        recommendation = json.loads(response.message)
        self.assertEqual(recommendation["tool_to_use"], "huggingface_hub_tool")
        self.assertIn("repository or file management", recommendation["reason"])

    def test_decision_tool_is_undetermined_for_ambiguous_task(self):
        # Test case for an ambiguous task description
        task_description = "I want to do something with Hugging Face."
        response = asyncio.run(self.tool.execute(task_description=task_description))

        recommendation = json.loads(response.message)
        self.assertEqual(recommendation["tool_to_use"], "undetermined")
        self.assertIn("ambiguous", recommendation["reason"])

if __name__ == '__main__':
    unittest.main()
