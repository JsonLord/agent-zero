import os
import sys
import json
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.embeddings'] = MagicMock()
sys.modules['langchain.embeddings.base'] = MagicMock()
sys.modules['pathspec'] = MagicMock()
sys.modules['watchdog'] = MagicMock()
sys.modules['watchdog.observers'] = MagicMock()
sys.modules['helpers.call_llm'] = MagicMock()
sys.modules['helpers.persist_chat'] = MagicMock()

import pytest
from helpers import dotenv, settings
from helpers.hf_space_defaults import apply_hf_space_defaults

def test_hf_space_defaults_all_three_vars(monkeypatch, tmp_path):
    dummy_key = "test-secret-never-log-this"
    monkeypatch.setenv("COMPATIBLE_URL", "https://example.test/v1")
    monkeypatch.setenv("COMPATIBLE_MODEL", "test-model")
    monkeypatch.setenv("BLABLADOR_API_KEY", dummy_key)

    apply_hf_space_defaults()

    saved_key = dotenv.get_dotenv_value("API_KEY_OTHER")
    assert saved_key == dummy_key

    from plugins._model_config.helpers import model_config
    presets = model_config.get_presets()
    assert presets[0]["chat"]["provider"] == "other"
    assert presets[0]["chat"]["api_base"] == "https://example.test/v1"
    assert presets[0]["chat"]["name"] == "test-model"

def test_hf_space_defaults_url_only(monkeypatch):
    monkeypatch.setenv("COMPATIBLE_URL", "https://example.test/v1")
    monkeypatch.delenv("COMPATIBLE_MODEL", raising=False)
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)

    apply_hf_space_defaults()

    from plugins._model_config.helpers import model_config
    presets = model_config.get_presets()
    assert presets[0]["chat"]["provider"] == "other"
    assert presets[0]["chat"]["api_base"] == "https://example.test/v1"

def test_hf_space_defaults_model_only(monkeypatch):
    monkeypatch.delenv("COMPATIBLE_URL", raising=False)
    monkeypatch.setenv("COMPATIBLE_MODEL", "test-model-only")
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)

    apply_hf_space_defaults()

    from plugins._model_config.helpers import model_config
    presets = model_config.get_presets()
    assert presets[0]["chat"]["provider"] == "other"
    assert presets[0]["chat"]["name"] == "test-model-only"

def test_hf_space_defaults_key_only(monkeypatch):
    dummy_key = "test-key-only"
    monkeypatch.delenv("COMPATIBLE_URL", raising=False)
    monkeypatch.delenv("COMPATIBLE_MODEL", raising=False)
    monkeypatch.setenv("BLABLADOR_API_KEY", dummy_key)

    apply_hf_space_defaults()

    saved_key = dotenv.get_dotenv_value("API_KEY_OTHER")
    assert saved_key == dummy_key

def test_hf_space_defaults_empty_vars(monkeypatch):
    monkeypatch.setenv("COMPATIBLE_URL", "")
    monkeypatch.setenv("COMPATIBLE_MODEL", "")
    monkeypatch.setenv("BLABLADOR_API_KEY", "")

    apply_hf_space_defaults()

def test_hf_space_defaults_unrelated_settings_preserved(monkeypatch):
    monkeypatch.setenv("COMPATIBLE_URL", "https://example.test/v1")
    current_settings = settings.get_settings()
    current_tz = current_settings.get("timezone")

    apply_hf_space_defaults()

    new_settings = settings.get_settings()
    assert new_settings.get("timezone") == current_tz

def test_hf_space_defaults_idempotent(monkeypatch):
    monkeypatch.setenv("COMPATIBLE_URL", "https://example.test/v1")
    monkeypatch.setenv("COMPATIBLE_MODEL", "test-model")
    monkeypatch.setenv("BLABLADOR_API_KEY", "secret-key")

    apply_hf_space_defaults()
    apply_hf_space_defaults()

    from plugins._model_config.helpers import model_config
    presets = model_config.get_presets()
    assert presets[0]["chat"]["provider"] == "other"

def test_hf_space_defaults_api_key_masked(monkeypatch, capsys):
    dummy_key = "test-secret-never-log-this"
    monkeypatch.setenv("BLABLADOR_API_KEY", dummy_key)

    apply_hf_space_defaults()

    captured = capsys.readouterr()
    assert dummy_key not in captured.out
    assert dummy_key not in captured.err

    current = settings.get_settings()
    current["api_keys"]["other"] = dummy_key
    out = settings.convert_out(current)
    masked = out["settings"]["api_keys"].get("other")
    assert masked == settings.API_KEY_PLACEHOLDER
    assert dummy_key not in json.dumps(out)
