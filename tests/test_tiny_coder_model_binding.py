import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


MODULE = "plugins._model_config.extensions.python.startup_migration._30_tiny_coder_env"


@pytest.fixture()
def module(monkeypatch):
    helpers = importlib.import_module("helpers")
    fake_dotenv = SimpleNamespace(save_dotenv_value=lambda *args: None)
    fake_plugins = SimpleNamespace(save_plugin_config=lambda *args: None)
    monkeypatch.setattr(helpers, "dotenv", fake_dotenv, raising=False)
    monkeypatch.setattr(helpers, "plugins", fake_plugins, raising=False)
    extension = ModuleType("helpers.extension")
    extension.Extension = object
    monkeypatch.setitem(sys.modules, "helpers.extension", extension)
    printing = ModuleType("helpers.print_style")
    printing.PrintStyle = SimpleNamespace(warning=lambda message: None)
    monkeypatch.setitem(sys.modules, "helpers.print_style", printing)
    package = ModuleType("plugins._model_config.helpers")
    package.model_config = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "plugins._model_config.helpers", package)
    sys.modules.pop(MODULE, None)
    return importlib.import_module(MODULE)


def test_tiny_coder_without_environment_inherits(monkeypatch, module):
    for key in (
        "TINY_CODER_PROVIDER",
        "TINY_CODER_MODEL",
        "TINY_CODER_API_BASE",
        "TINY_CODER_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    module.model_config.save_presets = lambda presets: (_ for _ in ()).throw(
        AssertionError("must not persist")
    )
    assert module.TinyCoderEnvironment().execute() == "inherited"


def test_tiny_coder_environment_selects_secret_free_profile_preset(monkeypatch, module):
    monkeypatch.setenv("TINY_CODER_PROVIDER", "other")
    monkeypatch.setenv("TINY_CODER_MODEL", "tiny-model")
    monkeypatch.setenv("TINY_CODER_API_BASE", "https://tiny.example/v1")
    monkeypatch.setenv("TINY_CODER_API_KEY", "dummy-secret")
    module.model_config.get_presets = lambda: [
        {"name": "Default", "chat": {"provider": "other", "name": "large"}}
    ]
    saved_presets, saved_configs, saved_keys = [], [], []
    module.model_config.save_presets = lambda presets: saved_presets.extend(presets)
    module.plugins.save_plugin_config = lambda *args: saved_configs.append(args)
    module.dotenv.save_dotenv_value = lambda *args: saved_keys.append(args)

    assert module.TinyCoderEnvironment().execute() == "configured"
    tiny = next(item for item in saved_presets if item["name"] == module.PRESET_NAME)
    assert tiny["chat"] == {
        "provider": "other",
        "name": "tiny-model",
        "api_base": "https://tiny.example/v1",
    }
    assert "dummy-secret" not in str(saved_presets)
    assert saved_configs == [
        ("_model_config", "", "tiny-coder", {"model_preset": module.PRESET_NAME})
    ]
    assert saved_keys == [("API_KEY_OTHER", "dummy-secret")]
