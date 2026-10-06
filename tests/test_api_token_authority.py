import asyncio
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Keep the auth contract runnable in the lightweight test interpreter. These
# stubs replace optional framework/model packages, not the helpers under test.
sys.modules.setdefault("models", MagicMock())
pytz = MagicMock()
pytz.common_timezones = ["UTC"]
pytz.timezone.side_effect = lambda value: value
pytz.exceptions.UnknownTimeZoneError = ValueError
sys.modules.setdefault("pytz", pytz)
sys.modules.setdefault(
    "simpleeval", MagicMock(simple_eval=lambda value, **kwargs: value)
)
sys.modules.setdefault("git", MagicMock())
sys.modules.setdefault("yaml", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())
sys.modules.setdefault("nest_asyncio", MagicMock(apply=lambda: None))
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
sys.modules.setdefault(
    "helpers.network", MagicMock(is_loopback_address=lambda value: True)
)
sys.modules.setdefault("helpers.rfc", MagicMock())
sys.modules.setdefault("helpers.defer", MagicMock())


class HttpResponse:
    def __init__(self, body="", status=200, *args, **kwargs):
        self.body = body
        self.status_code = status


request_proxy = SimpleNamespace(headers={}, json={})
flask = ModuleType("flask")
flask.Request = object
flask.Response = HttpResponse
flask.Flask = object
flask.jsonify = lambda value: value
flask.session = {}
flask.request = request_proxy
flask.send_file = flask.redirect = lambda *args, **kwargs: None
flask.url_for = lambda *args, **kwargs: "/"
sys.modules.setdefault("flask", flask)
werkzeug_response = ModuleType("werkzeug.wrappers.response")
werkzeug_response.Response = HttpResponse
sys.modules.setdefault("werkzeug.wrappers.response", werkzeug_response)

from helpers import api, settings


def test_deployment_token_overrides_configured_and_generated(monkeypatch):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "deployment-secret")
    monkeypatch.setattr(settings, "create_auth_token", lambda: "generated")
    assert settings.resolve_api_token("persisted") == "deployment-secret"
    normalized = settings.normalize_settings(
        {**settings.get_default_settings(), "mcp_server_token": "persisted"}
    )
    assert normalized["mcp_server_token"] == "deployment-secret"


def test_configured_then_generated_fallback(monkeypatch):
    monkeypatch.delenv("SPYNEL_AGENT_ZERO_API_KEY", raising=False)
    monkeypatch.setattr(settings, "create_auth_token", lambda: "generated")
    assert settings.resolve_api_token("persisted") == "persisted"
    assert settings.resolve_api_token("") == "generated"


@pytest.mark.parametrize(
    ("header", "expected"),
    [(None, 401), ("wrong", 401), ("deployment-secret", 200)],
)
def test_actual_api_decorator_uses_authoritative_token(monkeypatch, header, expected):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "deployment-secret")
    monkeypatch.setattr(settings, "get_settings", lambda: {"mcp_server_token": "old"})
    request_proxy.headers = {"X-API-KEY": header} if header else {}
    request_proxy.json = {}

    @api.requires_api_key
    async def protected():
        return HttpResponse("accepted", 200)

    response = asyncio.run(protected())
    assert response.status_code == expected


def test_save_reload_keeps_effective_deployment_token(monkeypatch, tmp_path):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "deployment-secret")
    monkeypatch.setattr(settings, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(settings, "_write_sensitive_settings", lambda value: None)
    monkeypatch.setattr(settings, "_settings", None)
    submitted = settings.get_default_settings()
    submitted["timezone"] = "UTC"
    settings.set_settings(submitted, apply=False)
    monkeypatch.setattr(settings, "_settings", None)
    assert settings.reload_settings()["mcp_server_token"] == "deployment-secret"


def test_public_settings_masks_authoritative_token(monkeypatch):
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "must-never-appear")
    monkeypatch.setattr(settings, "get_providers", lambda kind: [])
    monkeypatch.setattr(
        settings.subagents, "get_available_agents_dict", lambda context: {}
    )
    monkeypatch.setattr(
        settings.files, "get_subdirectories", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        settings.dotenv, "get_dotenv_value", lambda key, default=None: default
    )
    manager = SimpleNamespace(get_masked_secrets=lambda: "")
    monkeypatch.setattr(settings, "get_default_secrets_manager", lambda: manager)
    output = settings.convert_out(settings.get_default_settings())
    assert output["settings"]["mcp_server_token"] == settings.API_KEY_PLACEHOLDER
    assert "must-never-appear" not in str(output)
