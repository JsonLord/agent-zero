import os
import stat
from pathlib import Path
import pytest
from helpers import runtime_secrets, dotenv, files


def test_sync_runtime_secrets_maps_and_rotates(tmp_path, monkeypatch):
    env_file = tmp_path / "usr" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dotenv, "get_dotenv_file_path", lambda: str(env_file))
    monkeypatch.setattr(files, "get_abs_path", lambda *parts: str(tmp_path.joinpath(*parts)))

    # Set up initial persisted secret in .env
    dotenv.save_dotenv_value("HF_TOKEN", "old-hf-token")
    assert dotenv.get_dotenv_value("HF_TOKEN") == "old-hf-token"

    # Set new process env secret
    monkeypatch.setenv("HUGGINGFACE_TOKEN", "new-hf-token")
    monkeypatch.setenv("GITHUB_PAT", "pat-123")
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "spynel-sec")

    status = runtime_secrets.sync_runtime_secrets()

    assert os.environ["HF_TOKEN"] == "new-hf-token"
    assert os.environ["GH_TOKEN"] == "pat-123"
    assert os.environ["GITHUB_TOKEN"] == "pat-123"
    assert os.environ["SPYNEL_AGENT_ZERO_API_KEY"] == "spynel-sec"

    # Verify updated .env
    assert dotenv.get_dotenv_value("HF_TOKEN") == "new-hf-token"
    assert dotenv.get_dotenv_value("GH_TOKEN") == "pat-123"

    # Verify 0600 file permissions
    file_stat = env_file.stat().st_mode
    assert bool(file_stat & stat.S_IRUSR)
    assert bool(file_stat & stat.S_IWUSR)

    # Verify status dictionary contains only boolean presence flags
    assert status == {
        "spynel_api_key": True,
        "hf_token": True,
        "github_token": True,
    }
    assert "new-hf-token" not in str(status)
    assert "pat-123" not in str(status)


def test_get_secret_status_never_exposes_values(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "secret-hf")
    status = runtime_secrets.get_secret_status()
    assert status["hf_token"] is True
    assert "secret-hf" not in str(status)
