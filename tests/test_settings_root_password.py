import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
from typing import TypedDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# The focused settings contract does not exercise model inference. Keep this test
# runnable in the lightweight framework environment where those optional runtime
# dependencies are intentionally not installed.
sys.modules.setdefault("models", MagicMock())
if "pytz" not in sys.modules:
    pytz = MagicMock()
    pytz.common_timezones = ["UTC", "Europe/Rome"]
    pytz.timezone.side_effect = lambda value: value
    pytz.exceptions.UnknownTimeZoneError = ValueError
    sys.modules["pytz"] = pytz
sys.modules.setdefault("simpleeval", MagicMock(simple_eval=lambda value, **kwargs: value))
sys.modules.setdefault("git", MagicMock())
sys.modules.setdefault("yaml", MagicMock(safe_load=lambda value: {}, safe_dump=lambda value, **kwargs: "{}"))
sys.modules.setdefault("dotenv", MagicMock(load_dotenv=lambda *args, **kwargs: True, set_key=lambda *args, **kwargs: None))
sys.modules.setdefault("helpers.rfc", MagicMock())
sys.modules.setdefault("helpers.git", MagicMock())
sys.modules["helpers.git"].get_version.return_value = "test-version"
sys.modules.setdefault("helpers.subagents", MagicMock(get_available_agents_dict=lambda context: {}))
class _PrintStyle:
    def __init__(self, *args, **kwargs): pass
    def print(self, *args, **kwargs): pass
    warning = error = staticmethod(lambda *args, **kwargs: None)
sys.modules.setdefault("helpers.print_style", MagicMock(PrintStyle=_PrintStyle))
class _FieldOption(TypedDict):
    value: str
    label: str
sys.modules.setdefault("helpers.providers", MagicMock(get_providers=lambda kind: [], FieldOption=_FieldOption))
sys.modules.setdefault("helpers.secrets", MagicMock(get_default_secrets_manager=MagicMock))
sys.modules.setdefault("nest_asyncio", MagicMock(apply=lambda: None))

from helpers import settings


def _isolate_settings_writes(monkeypatch, tmp_path):
    saved_env: list[tuple[str, str]] = []
    monkeypatch.setattr(settings, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(
        settings.dotenv,
        "save_dotenv_value",
        lambda key, value: saved_env.append((key, value)),
    )
    secrets = MagicMock()
    monkeypatch.setattr(settings, "get_default_secrets_manager", lambda: secrets)
    return saved_env, secrets


def _non_root_docker(monkeypatch):
    monkeypatch.setattr(settings.runtime, "is_dockerized", lambda: True)
    monkeypatch.setattr(settings.os, "geteuid", lambda: 1000)


def test_non_root_docker_empty_root_password_saves_without_chpasswd(monkeypatch, tmp_path):
    _isolate_settings_writes(monkeypatch, tmp_path)
    _non_root_docker(monkeypatch)
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)
    submitted = settings.get_default_settings()
    submitted["root_password"] = ""

    settings._write_settings_file(submitted)

    run.assert_not_called()


def test_non_root_docker_placeholder_saves_without_chpasswd(monkeypatch, tmp_path):
    _isolate_settings_writes(monkeypatch, tmp_path)
    _non_root_docker(monkeypatch)
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)
    submitted = settings.get_default_settings()
    submitted["root_password"] = settings.PASSWORD_PLACEHOLDER

    settings._write_settings_file(submitted)

    run.assert_not_called()


def test_non_root_docker_unrelated_change_persists_without_chpasswd(monkeypatch, tmp_path):
    _isolate_settings_writes(monkeypatch, tmp_path)
    _non_root_docker(monkeypatch)
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)
    submitted = settings.get_default_settings()
    submitted.update(timezone="Europe/Rome", root_password="")

    settings._write_settings_file(submitted)

    assert json.loads(Path(settings.SETTINGS_FILE).read_text())["timezone"] == "Europe/Rome"
    run.assert_not_called()


def test_privileged_docker_changes_password_before_persisting_it(monkeypatch, tmp_path):
    saved_env, _ = _isolate_settings_writes(monkeypatch, tmp_path)
    monkeypatch.setattr(settings.runtime, "is_dockerized", lambda: True)
    monkeypatch.setattr(settings.os, "geteuid", lambda: 0)
    monkeypatch.setattr(settings.shutil, "which", lambda command: "/usr/sbin/chpasswd")
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)

    settings.set_root_password("new-secure-password")

    run.assert_called_once_with(
        ["chpasswd"],
        input=b"root:new-secure-password",
        capture_output=True,
        check=True,
    )
    assert saved_env == [(settings.dotenv.KEY_ROOT_PASSWORD, "new-secure-password")]


def test_non_root_explicit_password_is_ignored_and_not_persisted(monkeypatch, tmp_path):
    saved_env, _ = _isolate_settings_writes(monkeypatch, tmp_path)
    _non_root_docker(monkeypatch)
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)
    submitted = settings.get_default_settings()
    submitted.update(timezone="UTC", root_password="must-not-persist")

    settings._write_settings_file(submitted)

    run.assert_not_called()
    assert all(key != settings.dotenv.KEY_ROOT_PASSWORD for key, _ in saved_env)
    serialized = Path(settings.SETTINGS_FILE).read_text()
    assert "must-not-persist" not in serialized
    assert json.loads(serialized)["timezone"] == "UTC"


def test_capability_metadata_masks_secrets_in_non_root_runtime(monkeypatch):
    _non_root_docker(monkeypatch)
    monkeypatch.setattr(settings, "get_providers", lambda kind: [])
    monkeypatch.setattr(settings.subagents, "get_available_agents_dict", lambda context: {})
    monkeypatch.setattr(settings.files, "get_subdirectories", lambda *args, **kwargs: [])
    monkeypatch.setattr(settings.dotenv, "get_dotenv_value", lambda key, default=None: default)
    secrets = MagicMock()
    secrets.get_masked_secrets.return_value = "DUMMY_TOKEN=************"
    monkeypatch.setattr(settings, "get_default_secrets_manager", lambda: secrets)
    submitted = settings.get_default_settings()
    submitted["root_password"] = "root-password-must-not-leak"
    submitted["auth_password"] = "auth-password-must-not-leak"

    output = settings.convert_out(submitted)
    serialized = json.dumps(output)

    assert output["additional"]["root_password_supported"] is False
    assert output["additional"]["can_manage_root_password"] is False
    assert output["additional"]["is_dockerized"] is True
    assert output["additional"]["is_development"] is False
    assert "root-password-must-not-leak" not in serialized
    assert "auth-password-must-not-leak" not in serialized


def test_supported_root_password_failure_is_not_swallowed(monkeypatch, tmp_path):
    _isolate_settings_writes(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "can_manage_root_password", lambda: True)
    failure = settings.subprocess.CalledProcessError(1, ["chpasswd"])
    monkeypatch.setattr(settings.subprocess, "run", MagicMock(side_effect=failure))
    submitted = settings.get_default_settings()
    submitted["root_password"] = "not-in-the-error"

    try:
        settings._write_settings_file(submitted)
    except settings.subprocess.CalledProcessError as error:
        assert "not-in-the-error" not in str(error)
    else:
        raise AssertionError("supported root-password failures must propagate")


def test_non_root_end_to_end_sensitive_save_and_reload_contract(monkeypatch, tmp_path):
    saved_env, secrets = _isolate_settings_writes(monkeypatch, tmp_path)
    _non_root_docker(monkeypatch)
    run = MagicMock()
    monkeypatch.setattr(settings.subprocess, "run", run)
    submitted = settings.get_default_settings()
    submitted.update(
        timezone="Europe/Rome",
        auth_login="operator",
        auth_password="dummy-auth",
        root_password="unsupported-root",
        secrets="DUMMY_SECRET=dummy-value",
    )
    submitted["api_keys"] = {"other": "dummy-provider-key"}

    settings._write_settings_file(submitted)
    persisted = settings._read_settings_file()

    assert persisted["timezone"] == "Europe/Rome"
    assert persisted["api_keys"] == {}
    assert persisted["auth_login"] == ""
    assert persisted["auth_password"] == ""
    assert persisted["root_password"] == ""
    assert persisted["secrets"] == ""
    assert ("API_KEY_OTHER", "dummy-provider-key") in saved_env
    assert (settings.dotenv.KEY_AUTH_PASSWORD, "dummy-auth") in saved_env
    assert all(key != settings.dotenv.KEY_ROOT_PASSWORD for key, _ in saved_env)
    secrets.save_secrets_with_merge.assert_called_once_with("DUMMY_SECRET=dummy-value")
    run.assert_not_called()
    serialized = Path(settings.SETTINGS_FILE).read_text()
    for secret in ("dummy-provider-key", "dummy-auth", "unsupported-root", "dummy-value"):
        assert secret not in serialized
