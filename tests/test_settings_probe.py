import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _module(monkeypatch):
    fake_api = ModuleType("helpers.api")
    fake_api.ApiHandler = object
    fake_api.Request = object

    class Response:
        def __init__(self, body="", status=200):
            self.body = body
            self.status_code = status

    fake_api.Response = Response
    current = {"time_format": "12h"}
    fake_settings = ModuleType("helpers.settings")
    fake_settings.TIME_FORMAT_12H = "12h"
    fake_settings.TIME_FORMAT_24H = "24h"
    fake_settings.get_settings = lambda: current.copy()
    fake_settings.convert_out = lambda value: {"settings": value, "additional": {}}
    fake_settings.set_settings_delta = lambda delta: current.update(delta) or current.copy()
    fake_helpers = ModuleType("plugins._model_config.helpers")
    fake_helpers.model_config = SimpleNamespace(
        get_config=lambda: {
            "chat_model": {
                "provider": "other",
                "name": "alias-large",
                "api_base": "https://example.invalid/v1",
                "api_key": "must-not-leak",
            }
        }
    )
    monkeypatch.setitem(sys.modules, "helpers.api", fake_api)
    monkeypatch.setitem(sys.modules, "helpers.settings", fake_settings)
    import helpers
    monkeypatch.setattr(helpers, "settings", fake_settings, raising=False)
    monkeypatch.setitem(sys.modules, "plugins._model_config.helpers", fake_helpers)
    spec = importlib.util.spec_from_file_location("isolated_settings_probe", ROOT / "api/settings_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_settings_probe_is_api_key_protected_and_secret_safe(monkeypatch):
    module = _module(monkeypatch)
    handler = object.__new__(module.SettingsProbe)
    result = asyncio.run(handler.process({"action": "get"}, None))
    assert module.SettingsProbe.requires_api_key() is True
    assert module.SettingsProbe.requires_auth() is False
    assert module.SettingsProbe.requires_csrf() is False
    assert result["main_model"] == {
        "provider": "other",
        "name": "alias-large",
        "api_base": "https://example.invalid/v1",
    }
    assert "must-not-leak" not in str(result)


def test_settings_probe_allows_only_reversible_time_format(monkeypatch):
    module = _module(monkeypatch)
    handler = object.__new__(module.SettingsProbe)
    changed = asyncio.run(handler.process({"action": "set_time_format", "value": "24h"}, None))
    rejected = asyncio.run(handler.process({"action": "set_time_format", "value": "invalid"}, None))
    unknown = asyncio.run(handler.process({"action": "set_root_password", "value": "x"}, None))
    assert changed == {"ok": True, "time_format": "24h"}
    assert rejected.status_code == 400
    assert unknown.status_code == 400
