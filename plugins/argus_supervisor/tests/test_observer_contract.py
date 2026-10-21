"""Observer attachment uses real service/API/client paths without controller authority."""

import threading
from unittest.mock import AsyncMock

import pytest
from flask import Flask, Response

from helpers import api, cache
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.a2a_client import OpenTrainingA2AClient
from plugins.argus_supervisor.helpers.campaign_store import CampaignStore
from plugins.argus_supervisor.helpers.heartbeat import Supervisor
from plugins.argus_supervisor.helpers.models import SupervisorError


@pytest.fixture
def observer_service(tmp_path, monkeypatch):
    calls = []

    async def transport(method, suffix, payload):
        if method == "GET":
            return {"name": "Controlled OpenTraining", "skills": [], "capabilities": {}}
        calls.append(payload["method"])
        assert payload["method"] == "tasks/get"
        assert payload["params"]["id"] == "existing-task"
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {"id": "existing-task", "status": {"state": "completed"}},
        }

    client = OpenTrainingA2AClient("https://training.example/a2a", transport=transport)
    backend = AsyncMock()
    supervisor = Supervisor(CampaignStore(tmp_path), client, backend)
    monkeypatch.setenv("ARGUS_SUPERVISOR_ENABLED", "1")
    monkeypatch.setattr(service, "_instance", supervisor)
    for name in ("claim_control", "read_control", "mutate"):
        monkeypatch.setattr(client, name, AsyncMock(side_effect=AssertionError(name)))
    return supervisor, calls, backend


def create_observer():
    result = service.create(
        {
            "campaign_id": "observer-test",
            "objective": "Observe existing task",
            "remote_task_id": "existing-task",
            "max_attempts": 1,
        }
    )
    assert result["mode"] == "observer"
    assert result["controller_id"] is None and result["controller_epoch"] is None
    assert result["remote_task_id"] == "existing-task"
    return result


def assert_persisted(supervisor, calls, backend):
    campaign = supervisor.store.load("observer-test")
    assert campaign.remote_task_id == "existing-task"
    assert campaign.remote_state == "completed" and campaign.last_seen is not None
    assert campaign.mode == "observer"
    assert campaign.controller_id is None and campaign.controller_epoch is None
    assert calls == ["tasks/get"]
    for name in ("claim_control", "read_control", "mutate"):
        getattr(supervisor.client, name).assert_not_called()
    backend.notify.assert_not_called()
    backend.bind.assert_not_called()
    return campaign


@pytest.mark.asyncio
async def test_service_observer_attach_poll_and_read_need_no_authority(
    observer_service, monkeypatch
):
    supervisor, calls, backend = observer_service
    monkeypatch.setattr(
        supervisor, "authority", AsyncMock(side_effect=AssertionError("authority"))
    )
    monkeypatch.setattr(
        supervisor, "mutation", AsyncMock(side_effect=AssertionError("mutation"))
    )
    create_observer()
    await service.action("observer-test", "observe", {})
    assert_persisted(supervisor, calls, backend)
    supervisor.authority.assert_not_called()
    supervisor.mutation.assert_not_called()
    # Read from a new store instance, not the in-memory campaign returned by action.
    assert (
        CampaignStore(supervisor.store.root).load("observer-test").remote_state
        == "completed"
    )


def test_real_authenticated_plugin_api_observer_golden_path(
    observer_service, monkeypatch
):
    supervisor, calls, backend = observer_service
    monkeypatch.setattr("helpers.login.get_credentials_hash", lambda: "hash")
    monkeypatch.setattr(
        supervisor, "authority", AsyncMock(side_effect=AssertionError("authority"))
    )
    monkeypatch.setattr(
        supervisor, "mutation", AsyncMock(side_effect=AssertionError("mutation"))
    )
    app = Flask("observer_contract")
    app.secret_key = "test-session"
    app.add_url_rule("/", "serve_index", lambda: Response("index"))
    app.add_url_rule("/login", "login_handler", lambda: Response("login"))
    cache.clear(api.CACHE_AREA)
    api.register_api_route(app, threading.RLock())
    client = app.test_client()
    with client.session_transaction() as session:
        session["authentication"] = "hash"
        session["csrf_token"] = "test-csrf"
    headers = {"X-CSRF-Token": "test-csrf"}
    prefix = "/api/plugins/argus_supervisor/"
    try:
        response = client.post(
            prefix + "campaigns",
            json={
                "action": "create",
                "campaign_id": "observer-test",
                "objective": "Observe existing task",
                "remote_task_id": "existing-task",
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert response.get_json()["campaign"]["mode"] == "observer"
        response = client.post(
            prefix + "campaign_action",
            json={"campaign_id": "observer-test", "action": "observe"},
            headers=headers,
        )
        assert response.status_code == 200
        response = client.post(
            prefix + "campaigns", json={"campaign_id": "observer-test"}, headers=headers
        )
        assert response.status_code == 200
        persisted = response.get_json()["campaign"]
        assert (
            persisted["remote_state"] == "completed"
            and persisted["last_seen"] is not None
        )
        assert (
            persisted["remote_task_id"] == "existing-task"
            and persisted["mode"] == "observer"
        )
        assert (
            persisted["controller_id"] is None and persisted["controller_epoch"] is None
        )
        assert_persisted(supervisor, calls, backend)
        supervisor.authority.assert_not_called()
        supervisor.mutation.assert_not_called()
    finally:
        cache.clear(api.CACHE_AREA)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation,params",
    [
        ("submit", {"text": "Do not send"}),
        ("intervene", {"instruction": "Do not send"}),
        ("cancel", {"reason": "Do not send"}),
        ("release", {}),
    ],
)
async def test_observer_remote_mutations_still_fail_closed(
    observer_service, operation, params
):
    supervisor, calls, backend = observer_service
    create_observer()
    with pytest.raises(SupervisorError, match="^stale_controller_epoch$"):
        await service.action("observer-test", operation, params)
    assert calls == []
    for name in ("claim_control", "read_control", "mutate"):
        getattr(supervisor.client, name).assert_not_called()
    campaign = supervisor.store.load("observer-test")
    assert campaign.mode == "observer" and campaign.controller_epoch is None
    assert campaign.intent is None
    backend.notify.assert_not_called()
