import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from python.tools.developer_orchestrator import DeveloperOrchestrator
from agent import Agent, AgentConfig, AgentContext, LoopData
from python.helpers.tool import Response
import json

@pytest.fixture
def agent_config():
    return AgentConfig(
        chat_model=MagicMock(),
        utility_model=MagicMock(),
        embeddings_model=MagicMock(),
        browser_model=MagicMock(),
        mcp_servers=""
    )

@pytest.fixture
def agent_context(agent_config):
    return AgentContext(config=agent_config)

@pytest.fixture
def agent(agent_context):
    return Agent(0, agent_context.config, agent_context)

@pytest.fixture
def loop_data():
    return LoopData()

@pytest.mark.asyncio
async def test_start_state(agent, loop_data):
    # Mock the subordinate agent call
    mock_research_agent = AsyncMock()
    mock_research_agent.execute.return_value = Response(message="Research findings", break_loop=False)

    with patch.object(agent, 'get_tool', return_value=mock_research_agent):
        orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)

        response = await orchestrator.execute(message="Implement a new feature")

        assert "Based on your idea and my initial research" in response.message
        assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "awaiting_feedback"

@pytest.mark.asyncio
async def test_awaiting_feedback_state(agent, loop_data):
    # Set up the initial state
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "awaiting_feedback",
        "user_idea": "Implement a new feature",
        "research_findings": "Research findings"
    }

    # Mock the utility model call
    agent.call_utility_model = AsyncMock(return_value="Generated plan")

    orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)

    response = await orchestrator.execute(message="Looks good")

    assert "Thank you for your feedback" in response.message
    assert "Generated plan" in response.message
    assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "create_deployment_package"

@pytest.mark.asyncio
@patch("os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
@patch("shutil.copy")
async def test_create_deployment_package_state(mock_copy, mock_open, mock_makedirs, agent, loop_data):
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "create_deployment_package",
        "user_idea": "Implement a new feature",
        "plan": "Generated plan"
    }

    orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)
    response = await orchestrator.execute(message="")

    assert "The `/deployment` package has been created" in response.message
    assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "upload_to_github"
    mock_makedirs.assert_called_with("deployment", exist_ok=True)
    assert mock_open.call_count == 3
    assert mock_copy.call_count == 3

@pytest.mark.asyncio
@patch("subprocess.run")
async def test_upload_to_github_state_new_repo(mock_subprocess, agent, loop_data):
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "upload_to_github",
        "user_idea": "Implement a new feature"
    }

    with patch("builtins.open", MagicMock(read_data=json.dumps({"github_repo": "JsonLord/implement-a-new-feature", "branch": "main"}))):
        orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)
        response = await orchestrator.execute(message="")

    assert "Successfully created and pushed to GitHub repository" in response.message
    assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "awaiting_start_command"

@pytest.mark.asyncio
@patch("subprocess.run")
@patch("shutil.rmtree")
@patch("os.path.exists", return_value=False)
async def test_upload_to_github_state_existing_repo(mock_exists, mock_rmtree, mock_subprocess, agent, loop_data):
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "upload_to_github",
        "user_idea": "Implement a new feature",
        "github_repo": "JsonLord/existing-repo"
    }

    with patch("builtins.open", MagicMock(read_data=json.dumps({"github_repo": "JsonLord/existing-repo", "branch": "feature/implement-a-new-feature"}))):
        orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)
        response = await orchestrator.execute(message="")

    assert "Successfully pushed the deployment package to the new branch" in response.message
    assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "awaiting_start_command"

@pytest.mark.asyncio
@patch.dict(os.environ, {"HF_TOKEN": "test_token"})
async def test_awaiting_start_command_state(agent, loop_data):
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "awaiting_start_command",
        "user_idea": "Implement a new feature"
    }

    mock_jules_agent = AsyncMock()
    mock_jules_agent.execute.return_value = Response(message=json.dumps({"name": "session-123"}), break_loop=False)

    with patch.object(agent, 'get_tool', return_value=mock_jules_agent):
        with patch("builtins.open", MagicMock(read_data=json.dumps({"github_repo": "JsonLord/implement-a-new-feature", "branch": "main", "hf_space_name": "implement-a-new-feature", "hf_token_env_var": "HF_TOKEN"}))):
            orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)
            response = await orchestrator.execute(message="start")

    assert "Jules session started" in response.message
    assert loop_data.params_persistent["developer_orchestrator_data"]["state"] == "monitoring_jules"
    assert loop_data.params_persistent["developer_orchestrator_data"]["jules_session_id"] == "session-123"

@pytest.mark.asyncio
@patch("asyncio.create_task")
async def test_monitoring_jules_state(mock_create_task, agent, loop_data):
    loop_data.params_persistent["developer_orchestrator_data"] = {
        "state": "monitoring_jules",
        "jules_session_id": "session-123"
    }

    orchestrator = DeveloperOrchestrator(agent=agent, name="developer_orchestrator", method=None, args={}, message="", loop_data=loop_data)
    response = await orchestrator.execute(message="")

    assert "Jules session monitoring has started" in response.message
    mock_create_task.assert_called_once()
