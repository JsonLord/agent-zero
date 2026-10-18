import pytest
import asyncio
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_storage():
    class MockStorage:
        def __init__(self):
            self.last_update = None
        async def update_task(self, **kwargs):
            self.last_update = kwargs
    return MockStorage()

@pytest.fixture
def mock_broker():
    class MockBroker:
        pass
    return MockBroker()

@pytest.fixture
def a2a_worker(mock_broker, mock_storage):
    # Only import worker when tests run, after mocks might be applied
    import fasta2a
    from helpers.fasta2a_server import AgentZeroWorker
    return AgentZeroWorker(broker=mock_broker, storage=mock_storage)


@pytest.fixture(autouse=True)
def guard_agent_zero_initialization():
    import helpers.fasta2a_server

    """Make deterministic Argus A2A requests require:
    - no initialize_agent()
    - no AgentContext
    - no RFC configuration
    - no model provider
    - no LLM call
    - no normal Agent Zero chat initialization"""
    with patch("helpers.fasta2a_server.initialize_agent", side_effect=AssertionError("LLM/runtime path reached")) as init_mock, \
         patch("helpers.fasta2a_server.AgentContext", side_effect=AssertionError("AgentContext path reached")) as ctx_mock:
        yield { "init": init_mock, "ctx": ctx_mock }


async def test_supervisor_health_no_llm_call(a2a_worker):
    params = {
        "id": "task-123",
        "message": {
            "role": "user",
            "kind": "message",
            "message_id": "msg-1",
            "extensions": ["urn:openoperator:argus-supervisor:v1"],
            "metadata": {
                "urn:openoperator:argus-supervisor:v1": {
                    "operation": "supervisor.health",
                    "request_id": "req-1"
                }
            },
            "parts": [{"kind": "data", "data": {"params": {}}}]
        }
    }

    with patch("plugins.argus_supervisor.api.health.health_status", return_value={"enabled": True}) as health_mock, \
         patch("plugins.argus_supervisor.helpers.service.enabled", return_value=True) as enabled_mock:

        await a2a_worker.run_task(params)

    assert a2a_worker.storage.last_update is not None
    update = a2a_worker.storage.last_update
    assert update["task_id"] == "task-123"
    assert update["state"] == "completed"

    msg = update["new_messages"][0]
    assert "urn:openoperator:argus-supervisor:v1" in msg["extensions"]
    data_part = msg["parts"][0]
    assert data_part["kind"] == "data"

    result_data = data_part["data"]
    assert result_data["operation"] == "supervisor.health"
        # assert result_data.get("request_id") == "req-1"
    assert result_data.get("ok") is True



async def test_supervisor_status_no_llm_call(a2a_worker):
    params = {
        "id": "task-124",
        "message": {
            "role": "user",
            "kind": "message",
            "message_id": "msg-2",
            "extensions": ["urn:openoperator:argus-supervisor:v1"],
            "metadata": {
                "urn:openoperator:argus-supervisor:v1": {
                    "operation": "supervisor.status",
                    "request_id": "req-2"
                }
            },
            "parts": [{"kind": "data", "data": {"params": {}}}]
        }
    }

    with patch("plugins.argus_supervisor.helpers.service.get") as get_mock, \
         patch("plugins.argus_supervisor.helpers.service.enabled", return_value=True):
        mock_sup = MagicMock()
        mock_sup.last_tick = None
        mock_sup.last_error = None
        mock_sup.capabilities = {}
        mock_sup.store.ids.return_value = []
        get_mock.return_value = mock_sup

        await a2a_worker.run_task(params)

    update = a2a_worker.storage.last_update
    result_data = update["new_messages"][0]["parts"][0]["data"]
    assert result_data["operation"] == "supervisor.status"
    assert result_data["ok"] is True


async def test_ordinary_message_goes_to_agent_zero(a2a_worker, guard_agent_zero_initialization):
    # For this specific test, we EXPECT it to hit Agent Zero initialization
    guard_agent_zero_initialization["init"].side_effect = None
    guard_agent_zero_initialization["ctx"].side_effect = None

    mock_task = MagicMock()
    mock_task.result.return_value = asyncio.Future()
    mock_task.result.return_value.set_result("Agent response")

    mock_ctx = MagicMock()
    mock_ctx.communicate.return_value = mock_task
    mock_ctx.id = 'fake-id'

    guard_agent_zero_initialization["ctx"].return_value = mock_ctx

    params = {
        "id": "task-125",
        "message": {
            "role": "user",
            "kind": "message",
            "message_id": "msg-3",
            "parts": [{"kind": "text", "text": "Hello world"}]
        }
    }

    # We must mock remove_chat since we are stubbing out everything
    with patch("helpers.fasta2a_server.remove_chat"):
        await a2a_worker.run_task(params)

    guard_agent_zero_initialization["init"].assert_called_once()
    mock_ctx.communicate.assert_called_once()

    update = a2a_worker.storage.last_update
    msg = update["new_messages"][0]
    assert msg["parts"][0]["text"] == "Agent response"


async def test_unknown_operation_fails_safely(a2a_worker):
    params = {
        "id": "task-126",
        "message": {
            "role": "user",
            "kind": "message",
            "extensions": ["urn:openoperator:argus-supervisor:v1"],
            "metadata": {
                "urn:openoperator:argus-supervisor:v1": {
                    "operation": "unknown.op",
                    "request_id": "req-3"
                }
            },
            "parts": [{"kind": "data", "data": {"params": {}}}]
        }
    }

    with patch("plugins.argus_supervisor.helpers.service.enabled", return_value=True):
        await a2a_worker.run_task(params)

    update = a2a_worker.storage.last_update
    result_data = update["new_messages"][0]["parts"][0]["data"]
    assert result_data["operation"] == "unknown.op"
    assert result_data["ok"] is False
    assert "Unknown argus operation" in result_data["error"]


async def test_malformed_envelope_fails_safely(a2a_worker):
    # Missing operation metadata completely
    params = {
        "id": "task-127",
        "message": {
            "role": "user",
            "kind": "message",
            "extensions": ["urn:openoperator:argus-supervisor:v1"],
            "metadata": {},
            "parts": []
        }
    }

    with patch("plugins.argus_supervisor.helpers.service.enabled", return_value=True):
        await a2a_worker.run_task(params)

    update = a2a_worker.storage.last_update
    result_data = update["new_messages"][0]["parts"][0]["data"]
    assert result_data["operation"] is None
    assert result_data["ok"] is False


@pytest.mark.asyncio
async def test_agent_card_advertises_skills(guard_agent_zero_initialization):
    from helpers.fasta2a_server import DynamicA2AProxy

    proxy = DynamicA2AProxy.get_instance()

    # We shouldn't actually call _configure because it connects brokers, we just test skills locally but wait, we can just mock out Storage/Broker.
    with patch("helpers.fasta2a_server.AgentZeroFastA2A") as fasta2a_mock:
        proxy._configure()

    call_kwargs = fasta2a_mock.call_args.kwargs
    skills = call_kwargs["skills"]
    skill_ids = [s["id"] for s in skills]

    assert "general_assistance" in skill_ids
    assert "argus_supervisor_health" in skill_ids
    assert "argus_supervisor_status" in skill_ids
    assert "argus_campaign_list" in skill_ids
    assert "argus_campaign_control" in skill_ids
