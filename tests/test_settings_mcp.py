import asyncio
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules.setdefault("models", MagicMock())
if "pytz" not in sys.modules:
    pytz = MagicMock()
    pytz.common_timezones = ["UTC"]
    pytz.timezone.side_effect = lambda value: value
    pytz.exceptions.UnknownTimeZoneError = ValueError
    sys.modules["pytz"] = pytz
sys.modules.setdefault(
    "simpleeval", MagicMock(simple_eval=lambda value, **kwargs: value)
)
sys.modules.setdefault("git", MagicMock())
sys.modules.setdefault("yaml", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())
sys.modules.setdefault("nest_asyncio", MagicMock(apply=lambda: None))
sys.modules.setdefault("helpers.rfc", MagicMock())
sys.modules.setdefault("helpers.git", MagicMock(get_version=lambda: "test"))
sys.modules.setdefault(
    "helpers.subagents", MagicMock(get_available_agents_dict=lambda context: {})
)
sys.modules.setdefault("helpers.print_style", MagicMock(PrintStyle=MagicMock()))
sys.modules.setdefault(
    "helpers.providers", MagicMock(get_providers=lambda kind: [], FieldOption=dict)
)
sys.modules.setdefault(
    "helpers.secrets", MagicMock(get_default_secrets_manager=MagicMock)
)

import helpers.settings as settings_module


def test_apply_settings_updates_mcp_from_current_settings(monkeypatch):
    base_settings = settings_module.get_default_settings()
    previous_mcp_servers = '{"mcpServers": {}}'
    current_mcp_servers = (
        '{"mcpServers": {"deepwiki": {"url": "https://mcp.deepwiki.com/mcp"}}}'
    )
    previous = {
        **base_settings,
        "mcp_servers": previous_mcp_servers,
        "mcp_server_token": "unchanged-token",
    }
    current = {
        **base_settings,
        "mcp_servers": current_mcp_servers,
        "mcp_server_token": "unchanged-token",
    }
    received_mcp_servers: list[str] = []

    class FakeDeferredTask:
        def start_task(self, func, *args, **kwargs):
            asyncio.run(func(*args, **kwargs))
            return self

    class FakePrintStyle:
        def __init__(self, *args, **kwargs):
            pass

        def print(self, *args, **kwargs):
            pass

    class FakeMCPConfig:
        @classmethod
        def get_instance(cls):
            return cls()

        @classmethod
        def update(cls, mcp_servers):
            received_mcp_servers.append(mcp_servers)

        def model_dump_json(self):
            return "{}"

    agent_stub = ModuleType("agent")
    agent_stub.Agent = object

    class FakeAgentContext:
        @staticmethod
        def all():
            return []

    agent_stub.AgentContext = FakeAgentContext

    initialize_stub = ModuleType("initialize")
    initialize_stub.initialize_agent = lambda override_settings=None: None

    mcp_handler_stub = ModuleType("helpers.mcp_handler")
    mcp_handler_stub.MCPConfig = FakeMCPConfig

    monkeypatch.setitem(sys.modules, "agent", agent_stub)
    monkeypatch.setitem(sys.modules, "initialize", initialize_stub)
    monkeypatch.setitem(sys.modules, "helpers.mcp_handler", mcp_handler_stub)
    monkeypatch.setattr(settings_module, "_settings", current)
    monkeypatch.setattr(
        settings_module, "_apply_timezone_setting", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(settings_module.defer, "DeferredTask", FakeDeferredTask)
    monkeypatch.setattr(settings_module, "PrintStyle", FakePrintStyle)
    monkeypatch.setattr(
        settings_module.NotificationManager, "send_notification", lambda **kwargs: None
    )
    monkeypatch.setattr(settings_module, "create_auth_token", lambda: "unchanged-token")

    settings_module._apply_settings(previous)

    assert received_mcp_servers == [current_mcp_servers]
