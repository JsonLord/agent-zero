import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from python.tools.search_huggingface_space import SearchHuggingfaceSpace
from agent import Agent, AgentConfig, AgentContext, LoopData
from python.helpers.tool import Response
from gradio_client import Client

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
@patch('python.tools.search_huggingface_space.Client')
async def test_search_huggingface_space(mock_client, agent, loop_data):
    # Mock the Gradio client
    mock_predict = MagicMock(return_value=({'value': {"headers": ["ID", "Type"], "data": [["user/repo", "model"]]}},))
    mock_instance = MagicMock()
    mock_instance.predict = mock_predict
    mock_client.return_value = mock_instance

    tool = SearchHuggingfaceSpace(agent=agent, name="search_huggingface_space", method=None, args={}, message="", loop_data=loop_data)
    response = await tool.execute(search_str="test", repo_types=["model"], tags="text-generation")

    assert "ID: user/repo" in response.message
    assert "Type: model" in response.message
    mock_predict.assert_called_once_with(
        repo_types=["model"],
        sort="likes",
        sort_method="ascending order",
        filter_str="",
        search_str="test",
        author="",
        tags="text-generation",
        infer="all",
        gated="all",
        appr=["auto","manual"],
        size_categories=[],
        limit=1000,
        hardware=[],
        stage=[],
        fetch_detail=["Space Runtime"],
        show_labels=["Type","ID","Status","Gated","Likes","DLs","Trending","LastMod.","Pipeline"],
        api_name="/search"
    )

@pytest.mark.asyncio
@patch('python.tools.search_huggingface_space.Client')
async def test_search_huggingface_space_with_logs(mock_client, agent, loop_data):
    # Mock the Gradio client
    mock_predict = MagicMock(return_value=({'value': {"headers": ["ID", "Type"], "data": [["user/logs-repo", "space"]]}},))
    mock_instance = MagicMock()
    mock_instance.predict = mock_predict
    mock_client.return_value = mock_instance

    tool = SearchHuggingfaceSpace(agent=agent, name="search_huggingface_space", method=None, args={}, message="", loop_data=loop_data)
    response = await tool.execute(search_str="logs", repo_types=["space"])

    assert "ID: user/logs-repo" in response.message
    assert "Type: space" in response.message
    mock_predict.assert_called_once_with(
        repo_types=["space"],
        sort="likes",
        sort_method="ascending order",
        filter_str="",
        search_str="logs",
        author="",
        tags="",
        infer="all",
        gated="all",
        appr=["auto","manual"],
        size_categories=[],
        limit=1000,
        hardware=[],
        stage=[],
        fetch_detail=["Space Runtime"],
        show_labels=["Type","ID","Status","Gated","Likes","DLs","Trending","LastMod.","Pipeline"],
        api_name="/search"
    )
