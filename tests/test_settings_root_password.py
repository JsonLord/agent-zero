import json
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.embeddings'] = MagicMock()
sys.modules['langchain.embeddings.base'] = MagicMock()
sys.modules['models'] = MagicMock()

import pytest
from helpers import settings, runtime, dotenv

def test_non_root_docker_empty_root_password(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)

    mock_sub = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_sub)

    assert settings.can_manage_root_password() is False

    curr = settings.get_settings()
    curr["root_password"] = ""
    settings._write_sensitive_settings(curr)

    mock_sub.assert_not_called()

def test_non_root_docker_placeholder_password(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)

    mock_sub = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_sub)

    curr = settings.get_settings()
    curr["root_password"] = settings.PASSWORD_PLACEHOLDER
    settings._write_sensitive_settings(curr)

    mock_sub.assert_not_called()

def test_non_root_docker_unrelated_settings_change(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)

    mock_sub = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_sub)

    curr = settings.get_settings()
    curr["timezone"] = "UTC"
    curr["root_password"] = ""

    # Should complete without error
    settings._write_sensitive_settings(curr)
    mock_sub.assert_not_called()

def test_privileged_docker_root_password_functional(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")
    monkeypatch.setattr("os.geteuid", lambda: 0, raising=False)
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/sbin/chpasswd")

    mock_sub = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_sub)

    assert settings.can_manage_root_password() is True

    settings.set_root_password("new_secure_pass")
    mock_sub.assert_called_once()

def test_non_root_explicit_password_handled_safely(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)

    mock_sub = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_sub)

    curr = settings.get_settings()
    curr["root_password"] = "attempted_root_change"

    # Should handle safely without raising CalledProcessError
    settings._write_sensitive_settings(curr)
    mock_sub.assert_not_called()

def test_secret_leakage_protection(monkeypatch, capsys):
    dummy_secret = "test-secret-value-never-expose"
    monkeypatch.setenv("HF_SPACE", "true")

    curr = settings.get_settings()
    curr["auth_password"] = dummy_secret
    out = settings.convert_out(curr)

    captured = capsys.readouterr()
    assert dummy_secret not in captured.out
    assert dummy_secret not in captured.err
    assert dummy_secret not in json.dumps(out)
