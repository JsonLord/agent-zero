
import sys
from unittest.mock import MagicMock

fasta2a_mock = MagicMock()
fasta2a_mock.task_manager.TaskManager = object
sys.modules['fasta2a'] = fasta2a_mock
sys.modules['fasta2a.task_manager'] = fasta2a_mock.task_manager
sys.modules['fasta2a.schema'] = fasta2a_mock.schema
sys.modules['fasta2a.server'] = fasta2a_mock.server

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from helpers.blocking_a2a import BlockingTaskManager


pytestmark = pytest.mark.asyncio


def _make_request(task_id="task-123", blocking=False):
    return {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "message_id": task_id,
                "parts": [{"kind": "text", "text": "hello"}],
            },
            "configuration": {"blocking": blocking},
        },
    }


def _make_super_response(task_id="task-123", state="submitted"):
    return {
        "jsonrpc": "2.0",
        "id": "req-1",
        "result": {
            "task": {
                "id": task_id,
                "status": {"state": state},
            }
        },
    }


async def test_non_blocking_returns_immediately(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)
    req = _make_request(blocking=False)
    super_resp = _make_super_response("task-123", "submitted")

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        AsyncMock(return_value=super_resp),
    )

    resp = await tm.send_message(req)
    assert resp == super_resp
    storage.load_task.assert_not_called()


async def test_blocking_immediate_completion(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)
    req = _make_request(blocking=True)
    super_resp = _make_super_response("task-101", "submitted")

    completed_task = {
        "id": "task-101",
        "status": {"state": "completed"},
        "history": [],
    }

    storage.load_task = AsyncMock(return_value=completed_task)

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        AsyncMock(return_value=super_resp),
    )

    resp = await tm.send_message(req)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "req-1"
    assert resp["result"]["task"]["status"]["state"] == "completed"


async def test_blocking_delayed_completion(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)
    req = _make_request(blocking=True)
    super_resp = _make_super_response("task-202", "submitted")

    running_task = {
        "id": "task-202",
        "status": {"state": "running"},
        "history": [],
    }
    completed_task = {
        "id": "task-202",
        "status": {"state": "completed"},
        "history": [],
    }

    states = iter([running_task, running_task, completed_task])

    async def mock_load_task(task_id):
        return next(states)

    storage.load_task = mock_load_task

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        AsyncMock(return_value=super_resp),
    )

    start_time = time.monotonic()
    resp = await tm.send_message(req)
    elapsed = time.monotonic() - start_time

    assert resp["result"]["task"]["status"]["state"] == "completed"
    assert elapsed >= 0.9  # 2 polls * 0.5s sleep


async def test_blocking_failure_state(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)
    req = _make_request(blocking=True)
    super_resp = _make_super_response("task-303", "submitted")

    failed_task = {
        "id": "task-303",
        "status": {"state": "failed"},
        "history": [],
    }

    storage.load_task = AsyncMock(return_value=failed_task)

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        AsyncMock(return_value=super_resp),
    )

    resp = await tm.send_message(req)

    assert resp["result"]["task"]["status"]["state"] == "failed"


async def test_blocking_timeout_returns_current_task(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)
    req = _make_request(blocking=True)
    super_resp = _make_super_response("task-404", "submitted")

    working_task = {
        "id": "task-404",
        "status": {"state": "running"},
        "history": [],
    }

    storage.load_task = AsyncMock(return_value=working_task)
    monkeypatch.setenv("A2A_BLOCKING_TIMEOUT", "1")

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        AsyncMock(return_value=super_resp),
    )

    start_time = time.monotonic()
    resp = await tm.send_message(req)
    elapsed = time.monotonic() - start_time

    assert resp["result"]["task"]["status"]["state"] == "running"
    assert 0.9 <= elapsed <= 2.5


async def test_concurrent_blocking_requests(monkeypatch):
    broker = MagicMock()
    storage = MagicMock()

    tm = BlockingTaskManager(broker=broker, storage=storage)

    req_sync = _make_request("task-sync", blocking=True)
    req_async = _make_request("task-async", blocking=False)

    super_resp_sync = _make_super_response("task-sync", "submitted")
    super_resp_async = _make_super_response("task-async", "submitted")

    async def mock_send_message(self, request):
        task_id = request["params"]["message"]["message_id"]
        if request["params"].get("configuration", {}).get("blocking"):
            return _make_super_response(task_id, "submitted")
        return _make_super_response(task_id, "submitted")

    async def mock_load_task(task_id):
        if task_id == "task-sync":
            return {"id": "task-sync", "status": {"state": "completed"}}
        return {"id": "task-async", "status": {"state": "submitted"}}

    storage.load_task = mock_load_task

    monkeypatch.setattr(
        "fasta2a.task_manager.TaskManager.send_message",
        mock_send_message,
    )

    res_sync, res_async = await asyncio.gather(
        tm.send_message(req_sync),
        tm.send_message(req_async),
    )

    assert res_sync["result"]["task"]["status"]["state"] == "completed"
    assert res_async["result"]["task"]["status"]["state"] == "submitted"
