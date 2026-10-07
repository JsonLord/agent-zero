import copy
import importlib.util
import json
import sys
import types
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture()
def isolated(monkeypatch):
    presets = [
        {
            "name": "Default",
            "chat": {"provider": "openai", "name": "old-main", "api_base": "old"},
            "utility": {"provider": "other", "name": "alias-fast", "api_base": "utility"},
            "embedding": {"provider": "huggingface", "name": "sentence-transformers/all-MiniLM-L6-v2"},
        }
    ]
    saved = []
    fake_dotenv = types.ModuleType("helpers.dotenv")
    fake_dotenv.save_dotenv_value = lambda key, value: saved.append((key, value))
    fake_print = types.ModuleType("helpers.print_style")
    class PrintStyle:
        @staticmethod
        def warning(message): pass
    fake_print.PrintStyle = PrintStyle

    parent_pkg = sys.modules.get("plugins._model_config.helpers")
    if not parent_pkg:
        parent_pkg = types.ModuleType("plugins._model_config.helpers")
        monkeypatch.setitem(sys.modules, "plugins._model_config.helpers", parent_pkg)

    fake_model = types.ModuleType("plugins._model_config.helpers.model_config")
    fake_model.get_presets = lambda: copy.deepcopy(presets)
    fake_model.save_presets = lambda value: presets.__setitem__(slice(None), copy.deepcopy(value))

    monkeypatch.setattr(parent_pkg, "model_config", fake_model, raising=False)
    monkeypatch.setitem(sys.modules, "plugins._model_config.helpers.model_config", fake_model)
    monkeypatch.setitem(sys.modules, "helpers.dotenv", fake_dotenv)
    monkeypatch.setitem(sys.modules, "helpers.print_style", fake_print)

    import helpers
    monkeypatch.setattr(helpers, "dotenv", fake_dotenv, raising=False)
    spec = importlib.util.spec_from_file_location("isolated_hf_defaults", ROOT / "helpers/hf_space_defaults.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, presets, saved


def env(monkeypatch, url=None, model=None, key=None):
    for name, value in (("COMPATIBLE_URL", url), ("COMPATIBLE_MODEL", model), ("BLABLADOR_API_KEY", key)):
        if value is None: monkeypatch.delenv(name, raising=False)
        else: monkeypatch.setenv(name, value)


def test_all_three_vars_select_native_compatible_main_without_touching_other_slots(isolated, monkeypatch, capsys):
    module, presets, saved = isolated; before = copy.deepcopy(presets[0]); env(monkeypatch, "https://example.test/v1", "alias-large", "dummy-secret")
    summary = module.apply_hf_space_defaults()
    assert summary == {"url": True, "model": True, "api_key": True}
    assert presets[0]["chat"] == {"provider": "other", "name": "alias-large", "api_base": "https://example.test/v1"}
    assert presets[0]["utility"] == before["utility"] and presets[0]["embedding"] == before["embedding"]
    assert saved == [("API_KEY_OTHER", "dummy-secret")] and "api_key" not in presets[0]["chat"]
    captured = capsys.readouterr(); assert "dummy-secret" not in captured.out + captured.err


@pytest.mark.parametrize(("values", "expected", "saved_key"), [
    (("https://new/v1", None, None), ("other", "old-main", "https://new/v1"), False),
    ((None, "new-main", None), ("other", "new-main", "old"), False),
    ((None, None, "token"), ("openai", "old-main", "old"), True),
    (("", "", ""), ("openai", "old-main", "old"), False),
])
def test_nonempty_values_authoritative_and_absence_preserves(isolated, monkeypatch, values, expected, saved_key):
    module, presets, saved = isolated; env(monkeypatch, *values); module.apply_hf_space_defaults(); chat = presets[0]["chat"]
    assert (chat["provider"], chat["name"], chat["api_base"]) == expected
    assert bool(saved) == saved_key


def test_defaults_idempotent_and_token_never_serialized(isolated, monkeypatch, capsys):
    module, presets, saved = isolated; env(monkeypatch, "https://example.test/v1", "alias-large", "never-print")
    module.apply_hf_space_defaults(); first = copy.deepcopy(presets); module.apply_hf_space_defaults()
    assert presets == first and "never-print" not in json.dumps(presets)
    captured = capsys.readouterr(); assert "never-print" not in captured.out + captured.err


def test_native_model_config_integration(tmp_path, monkeypatch):
    """Integration test exercising native model_config against a temp directory."""
    from helpers import files
    from helpers.hf_space_defaults import apply_hf_space_defaults
    from plugins._model_config.helpers import model_config

    real_get_abs_path = files.get_abs_path
    def fake_get_abs_path(*parts):
        if parts and parts[0] == files.USER_DIR and len(parts) > 1 and parts[1] == files.PLUGINS_DIR:
            return str(tmp_path.joinpath(*parts))
        return real_get_abs_path(*parts)

    monkeypatch.setattr(files, "get_abs_path", fake_get_abs_path)

    initial_presets = [
        {
            "name": "Default",
            "chat": {"provider": "openai", "name": "gpt-4o", "api_base": "https://api.openai.com/v1"},
            "utility": {"provider": "openai", "name": "gpt-4o-mini"},
            "embedding": {"provider": "huggingface", "name": "sentence-transformers/all-MiniLM-L6-v2"},
        }
    ]
    model_config.save_presets(initial_presets)

    env(monkeypatch, "https://native-compatible.test/v1", "native-model-v1", "native-key-123")
    apply_hf_space_defaults()

    saved_presets = model_config.get_presets()
    assert saved_presets[0]["chat"]["provider"] == "other"
    assert saved_presets[0]["chat"]["name"] == "native-model-v1"
    assert saved_presets[0]["chat"]["api_base"] == "https://native-compatible.test/v1"
