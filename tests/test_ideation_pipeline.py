import pytest
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, call

# Mock the necessary parts of the agent and its tools
class MockAgent:
    def __init__(self):
        self.loop_data = {}
        self.call_tool = AsyncMock()
        self.config = MagicMock()
        self.config.ideation_repo = "test/repo"

@pytest.fixture
def mock_agent():
    return MockAgent()

@pytest.mark.asyncio
async def test_initiate_ideate_session(mock_agent):
    """Tests the InitiateIdeateSession tool."""
    from python.tools.initiate_ideate_session import InitiateIdeateSession

    tool = InitiateIdeateSession(agent=mock_agent, name="initiate_ideate_session", method=None, args={}, message="", loop_data=mock_agent.loop_data)

    project_name = "Test Project"
    response = await tool.execute(project_name=project_name)

    assert "Error" not in response.message
    assert "ideation_log_path" in mock_agent.loop_data
    log_path = mock_agent.loop_data['ideation_log_path']
    assert os.path.exists(log_path)

    with open(log_path, 'r') as f:
        content = f.read()
        assert f"# Ideation Session: {project_name}" in content

    # Clean up
    os.remove(log_path)
    os.rmdir(os.path.dirname(log_path))

@pytest.mark.asyncio
async def test_end_ideate_session(mock_agent):
    """Tests the EndIdeateSession tool."""
    from python.tools.end_ideate_session import EndIdeateSession

    # Setup a mock session
    project_name = "Test Project End"
    session_dir = "/app/ideate/test_session"
    log_path = os.path.join(session_dir, "session_log.md")
    os.makedirs(session_dir, exist_ok=True)
    with open(log_path, 'w') as f:
        f.write("# Test Log")
    mock_agent.loop_data['ideation_log_path'] = log_path

    tool = EndIdeateSession(agent=mock_agent, name="end_ideate_session", method=None, args={}, message="", loop_data=mock_agent.loop_data)

    response = await tool.execute()

    assert "Error" not in response.message
    assert mock_agent.loop_data['ideation_log_path'] is None

    # Verify the git-agent was called
    assert mock_agent.call_tool.call_count == 2
    # Check that the call was made with a string command
    for mock_call in mock_agent.call_tool.call_args_list:
        args, kwargs = mock_call
        assert args[0] == "git-agent"
        if 'command' in kwargs and 'create_branch' in kwargs['command']:
            assert "test/repo" in kwargs['command']
        elif 'repo' in kwargs:
            assert kwargs['repo'] == "test/repo"

    # Clean up
    os.remove(log_path)
    os.rmdir(session_dir)

# This test is more complex as it involves the agent's main loop.
# For now, we'll focus on unit testing the tools. A more complete
# test would involve a mock of the agent's `_process_chain` method.
