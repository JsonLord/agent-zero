import os
import shutil
import asyncio
from unittest.mock import MagicMock
import pytest
from python.extensions.message_loop_prompts_before._10_keyword_personas import KeywordPersonas
from agent import Agent, AgentContext, AgentConfig
import models
from python.helpers.tool import Tool

# Mock the models module to prevent actual model loading
@pytest.fixture(autouse=True)
def mock_models(monkeypatch):
    # Mock the get_chat_model function to return a MagicMock
    mock_get_model = MagicMock()
    monkeypatch.setattr(models, "get_chat_model", mock_get_model)
    monkeypatch.setattr(models, "get_embedding_model", mock_get_model)
    monkeypatch.setattr(models, "get_browser_model", mock_get_model)

@pytest.fixture
def mock_agent_config():
    # Return a mocked AgentConfig with necessary attributes
    return AgentConfig(
        chat_model=MagicMock(),
        utility_model=MagicMock(),
        embeddings_model=MagicMock(),
        browser_model=MagicMock(),
        mcp_servers="",
        profile=None
    )

@pytest.fixture
def mock_agent(mock_agent_config):
    # Setup a mock Agent with a mocked AgentContext and AgentConfig
    mock_context = MagicMock(spec=AgentContext)
    mock_context.log = MagicMock()
    agent = Agent(number=0, config=mock_agent_config, context=mock_context)
    agent.config.profile = None # Ensure profile is None for default prompt path
    return agent

@pytest.fixture
def keyword_personas(mock_agent):
    # Instantiate KeywordPersonas correctly as a Tool
    return KeywordPersonas(
        agent=mock_agent,
        name="keyword_personas",
        method=None,
        args={},
        message="",
        loop_data=None
    )

@pytest.fixture(autouse=True)
def setup_teardown_prompts():
    # Create temporary directories and prompt files for testing
    keywords_path = "prompts/keywords"
    os.makedirs(keywords_path, exist_ok=True)

    with open(os.path.join(keywords_path, "develop.md"), "w") as f:
        f.write("Develop mode")
    with open(os.path.join(keywords_path, "search.md"), "w") as f:
        f.write("Search mode for {{query}}")

    yield

    # Cleanup the created files and directories
    shutil.rmtree(keywords_path, ignore_errors=True)

@pytest.mark.asyncio
async def test_execute_with_keyword(keyword_personas):
    message = "develop something"
    result = await keyword_personas.execute(message)
    assert "Develop mode" in result
    assert message in result

@pytest.mark.asyncio
async def test_execute_with_parameterized_keyword(keyword_personas):
    message = "search for something"
    result = await keyword_personas.execute(message)
    assert "Search mode for for something" in result
    assert message in result

@pytest.mark.asyncio
async def test_execute_with_no_keyword(keyword_personas):
    message = "do something"
    result = await keyword_personas.execute(message)
    assert result == message
