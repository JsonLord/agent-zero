import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "hf_smoke", ROOT / "scripts/smoke_hf_openoperator.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def settings_payload(time_format="12h"):
    return {
        "settings": {"time_format": time_format, "mcp_server_token": "************"},
        "additional": {
            "is_dockerized": True,
            "is_development": False,
            "root_password_supported": False,
        },
        "runtime": {"uid": 1000, "gid": 1000},
        "main_model": {
            "provider": "other",
            "name": "alias-large",
            "api_base": "https://example.invalid/v1",
        },
    }


def test_smoke_uses_only_named_environment_and_never_prints_values(monkeypatch, capsys):
    secret = "secret-that-must-never-print"
    smoke.API_KEY = secret
    smoke.HF_TOKEN = secret
    smoke.results = []
    monkeypatch.setattr(smoke.time, "sleep", lambda value: None)
    polls = {"chat": "chat-ok"}

    def fake(path, payload=None, api=False):
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/api/settings_probe":
            if payload.get("action") == "set_time_format":
                return 200, {"time_format": payload["value"]}
            return 200, settings_payload("24h" if polls.get("changed") else "12h")
        if path.endswith("api_message"):
            if payload["agent_profile"] == "definitely-not-real":
                return 404, {"error": "not found"}
            return 200, {"context_id": "chat"}
        if path.endswith("api_poll"):
            return 200, {"status": "completed", "result": "hi"}
        if path.endswith("delegate"):
            return 200, {"context_id": "specialist", "goal_id": "goal_1"}
        if path == "/api/agents":
            return 200, {
                "ok": True,
                "data": [{"key": name} for name in smoke.REQUIRED_PROFILES],
            }
        if path.endswith("skills_catalog"):
            return 200, {"ok": True, "skills": [{"name": "paperclip-board-manager"}]}
        if path.endswith("agent_profile_create"):
            return 403, {"error": "protected"}
        raise AssertionError(path)

    monkeypatch.setattr(smoke, "request", fake)
    # Keep the reversible write stateful.
    original = fake

    def stateful(path, payload=None, api=False):
        if path == "/api/settings_probe" and payload.get("action") == "set_time_format":
            polls["changed"] = payload["value"] == "24h"
            return 200, {"time_format": payload["value"]}
        return original(path, payload, api)

    monkeypatch.setattr(smoke, "request", stateful)
    assert smoke.main() == 0
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    for label in (
        "health: PASS",
        "chat: PASS",
        "delegation: PASS",
        "unknown profile safety: PASS",
        "profile-create protection: PASS",
        "specialist profiles: PASS",
        "Spynel: PASS",
        "Paperclip skill: PASS",
    ):
        assert label in captured.out


def test_smoke_polls_delegated_goal_and_reports_attention(monkeypatch, capsys):
    smoke.API_KEY = "configured"
    smoke.HF_TOKEN = ""
    smoke.results = []
    monkeypatch.setattr(smoke.time, "sleep", lambda value: None)
    poll_count = 0

    def fake(path, payload=None, api=False):
        nonlocal poll_count
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/api/settings_probe":
            if payload.get("action") == "set_time_format":
                return 200, {"time_format": payload["value"]}
            return 200, settings_payload()
        if path.endswith("api_message"):
            if payload["agent_profile"] == "definitely-not-real":
                return 404, {}
            return 200, {"context_id": "chat"}
        if path.endswith("delegate"):
            return 200, {"context_id": "goal-context", "goal_id": "goal-1"}
        if path.endswith("api_poll"):
            poll_count += 1
            if payload["context_id"] == "goal-context":
                return 200, {
                    "status": "working",
                    "requires_attention": True,
                    "attention_reason": "manual_action_required",
                }
            return 200, {"status": "completed", "result": "hi"}
        if path == "/api/agents":
            return 200, {"data": [{"key": name} for name in smoke.REQUIRED_PROFILES]}
        if path.endswith("skills_catalog"):
            return 200, {"skills": [{"name": "paperclip-board-manager"}]}
        if path.endswith("agent_profile_create"):
            return 403, {}
        raise AssertionError(path)

    monkeypatch.setattr(smoke, "request", fake)
    assert smoke.main() == 1
    assert poll_count == 3
    assert "delegation: BLOCKED" in capsys.readouterr().out


def test_smoke_without_api_key_exits_nonzero(monkeypatch, capsys):
    smoke.API_KEY = ""
    smoke.HF_TOKEN = ""
    smoke.results = []
    monkeypatch.setattr(
        smoke,
        "request",
        lambda path, payload=None, api=False: (
            (200, {"status": "ok"}) if path == "/health" else (403, {})
        ),
    )
    assert smoke.main() == 1
    assert "chat: BLOCKED" in capsys.readouterr().out
