import asyncio
from types import SimpleNamespace

import pytest

from agent import AgentContextType
from plugins._chat_naming.commands import rename_command
from plugins._chat_naming.extensions.python.monologue_end import (
    _60_rename_chat as rename_chat,
)
from plugins._chat_naming.helpers import naming


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def scoped_config(monkeypatch):
    monkeypatch.setattr(
        naming.plugins,
        "get_plugin_config",
        lambda *args, **kwargs: {
            "automatic_naming": True,
            "automatic_naming_mode": "once",
            "automatic_naming_timeout_seconds": 45,
        },
    )


class _Message:
    def __init__(self, content, *, ai=False, sequence=0):
        self.content = content
        self.ai = ai
        self.sequence = sequence


class _History:
    def __init__(self, messages):
        self._messages = messages

    def all_messages(self):
        return list(self._messages)


class _Agent:
    def __init__(self, messages, *, name="", response="Generated Name"):
        self.context = SimpleNamespace(
            id="ctx-naming",
            name=name,
            type=AgentContextType.USER,
        )
        self.context.agent0 = self
        self.history = _History(messages)
        self.config = SimpleNamespace(profile="agent0")
        self._response = response
        self.utility_calls = []

    def read_prompt(self, name, **kwargs):
        return f"{name}:{kwargs}"

    async def call_utility_model(self, **kwargs):
        self.utility_calls.append(kwargs)
        return self._response


async def test_user_message_selection_excludes_assistant_work_and_tool_results():
    agent = _Agent(
        [
            _Message({"user_message": "Plan a launch"}, sequence=1),
            _Message(
                {"tool_name": "search", "tool_result": "internal work"}, sequence=2
            ),
            _Message("assistant response", ai=True, sequence=3),
            _Message({"user_intervention": "Okay, do it"}, sequence=4),
        ]
    )

    assert naming.get_user_messages(agent) == ["Plan a launch", "Okay, do it"]
    assert naming.latest_user_sequence(agent) == 4


async def test_once_mode_uses_first_message_and_does_not_override_a_name(monkeypatch):
    scheduled = []
    agent = _Agent(
        [
            _Message({"user_message": "First request"}, sequence=1),
            _Message({"user_message": "Second request"}, sequence=2),
        ]
    )
    monkeypatch.setattr(
        rename_chat.naming,
        "get_config",
        lambda _agent: {"automatic_naming": True, "automatic_naming_mode": "once"},
    )
    original_create_task = asyncio.create_task

    def schedule(coro):
        task = original_create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(rename_chat.asyncio, "create_task", schedule)

    await rename_chat.RenameChat(agent=agent).execute()
    assert len(scheduled) == 1

    captured = {}

    async def generate(_agent, **kwargs):
        captured.update(kwargs)
        return "First Request"

    saved = []
    monkeypatch.setattr(rename_chat.naming, "generate_name", generate)
    monkeypatch.setattr(
        rename_chat.naming,
        "save_context_name",
        lambda _agent, name: saved.append(name),
    )
    monkeypatch.setattr(rename_chat.AgentContext, "get", lambda _id: agent.context)
    await scheduled.pop()

    assert captured["user_messages"] == ["First request"]
    assert saved == ["First Request"]

    agent.context.name = "Manual Name"
    await rename_chat.RenameChat(agent=agent).execute()
    assert scheduled == []


async def test_always_mode_passes_recent_user_context(monkeypatch):
    messages = [
        _Message({"user_message": f"Message {number}"}, sequence=number)
        for number in range(1, 7)
    ]
    agent = _Agent(messages, name="Existing Name")
    scheduled = []
    monkeypatch.setattr(
        rename_chat.naming,
        "get_config",
        lambda _agent: {"automatic_naming": True, "automatic_naming_mode": "always"},
    )
    original_create_task = asyncio.create_task

    def schedule(coro):
        task = original_create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(rename_chat.asyncio, "create_task", schedule)

    await rename_chat.RenameChat(agent=agent).execute()
    captured = {}

    async def generate(_agent, **kwargs):
        captured.update(kwargs)
        return "Current Topic"

    monkeypatch.setattr(rename_chat.naming, "generate_name", generate)
    monkeypatch.setattr(rename_chat.naming, "save_context_name", lambda *_args: None)
    monkeypatch.setattr(rename_chat.AgentContext, "get", lambda _id: agent.context)
    await scheduled.pop()

    assert captured["user_messages"] == [
        "Message 3",
        "Message 4",
        "Message 5",
        "Message 6",
    ]
    assert captured["current_name"] == "Existing Name"


async def test_rename_failure_sends_scoped_utility_model_notification(monkeypatch):
    sent = []
    agent = _Agent([_Message({"user_message": "Plan a launch"}, sequence=1)])

    async def fail(*_args, **_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(rename_chat.naming, "generate_name", fail)
    monkeypatch.setattr(
        rename_chat.NotificationManager,
        "send_notification",
        lambda **kwargs: sent.append(kwargs),
    )

    await rename_chat.RenameChat(agent=agent).change_name(
        messages=["Plan a launch"],
        request_sequence=1,
        only_if_unnamed=True,
    )

    assert len(sent) == 1
    assert sent[0]["type"] == rename_chat.NotificationType.ERROR
    assert sent[0]["title"] == "Chat Naming Failed"
    assert sent[0]["id"] == "chat_naming_failed_ctx-naming"


async def test_generated_name_is_normalized_and_bounded(monkeypatch):
    agent = _Agent(
        [_Message({"user_message": "Plan the release"}, sequence=1)],
        response='  "A very long generated release planning title that should be shortened"  ',
    )
    monkeypatch.setattr(
        "plugins._model_config.helpers.model_config.get_utility_model_config",
        lambda _agent: {"ctx_length": 1000},
    )

    result = await naming.generate_name(agent)

    assert len(result) <= naming.GENERATED_NAME_LIMIT
    assert result.endswith("...")
    assert agent.utility_calls[0]["background"] is True


async def test_naming_input_stays_within_utility_context_budget(monkeypatch):
    agent = _Agent(
        [
            _Message({"user_message": "older context " * 2000}, sequence=1),
            _Message({"user_message": "LATEST_CONTEXT " * 2000}, sequence=2),
        ],
        response="Budgeted Name",
    )
    monkeypatch.setattr(
        "plugins._model_config.helpers.model_config.get_utility_model_config",
        lambda _agent: {"ctx_length": 300},
    )

    await naming.generate_name(agent)

    call = agent.utility_calls[0]
    estimated_tokens = naming.tokens.approximate_tokens(
        call["system"]
    ) + naming.tokens.approximate_tokens(call["message"])
    assert estimated_tokens <= int(300 * naming.UTILITY_CONTEXT_INPUT_RATIO)
    assert "LATEST_CONTEXT" in call["message"]
    assert "older context" not in call["message"]


async def test_manual_api_generates_and_saves_with_target_chat_agent(monkeypatch):
    from plugins._chat_naming.api import chat_name

    agent = _Agent([_Message({"user_message": "Name this chat"}, sequence=1)])
    monkeypatch.setattr(chat_name.AgentContext, "get", lambda _id: agent.context)

    async def generate(target_agent, **kwargs):
        assert target_agent is agent
        assert kwargs["current_name"] == ""
        return "Generated Chat"

    saved = []
    monkeypatch.setattr(chat_name.naming, "generate_name", generate)
    monkeypatch.setattr(
        chat_name.naming,
        "save_context_name",
        lambda target_agent, name: saved.append((target_agent, name)),
    )
    handler = object.__new__(chat_name.ChatName)

    generated = await handler.process(
        {"action": "generate", "kind": "chat", "item_id": agent.context.id},
        None,
    )
    renamed = await handler.process(
        {
            "action": "save",
            "kind": "chat",
            "item_id": agent.context.id,
            "name": "  Manual   Chat  ",
        },
        None,
    )

    assert generated == {"ok": True, "name": "Generated Chat"}
    assert renamed == {"ok": True, "name": "Manual Chat"}
    assert saved == [(agent, "Manual Chat")]


async def test_rename_command_saves_a_custom_name(monkeypatch):
    agent = _Agent([_Message({"user_message": "Plan a launch"}, sequence=1)])
    saved = []
    monkeypatch.setattr(
        rename_command.naming,
        "save_context_name",
        lambda target_agent, name: saved.append((target_agent, name)) or name,
    )

    result = await rename_command.run(
        {
            "invocation": {"raw_arguments": "New Chat Name"},
            "context": {"agent": agent},
        }
    )

    assert saved == [(agent, "New Chat Name")]
    assert result == {
        "text": "",
        "effects": [
            {
                "type": "toast",
                "message": 'Chat renamed to "New Chat Name".',
                "level": "success",
            }
        ],
    }


async def test_rename_auto_generates_and_saves_a_name(monkeypatch):
    agent = _Agent([_Message({"user_message": "Plan a launch"}, sequence=1)])
    generated = []
    saved = []

    async def generate(target_agent):
        generated.append(target_agent)
        return "Launch Plan"

    monkeypatch.setattr(rename_command.naming, "generate_name", generate)
    monkeypatch.setattr(
        rename_command.naming,
        "save_context_name",
        lambda target_agent, name: saved.append((target_agent, name)) or name,
    )

    result = await rename_command.run(
        {
            "invocation": {"raw_arguments": "auto"},
            "context": {"agent": agent},
        }
    )

    assert generated == [agent]
    assert saved == [(agent, "Launch Plan")]
    assert result["effects"][0]["message"] == 'Chat renamed to "Launch Plan".'


async def test_manual_task_rename_updates_scheduler_and_context(monkeypatch):
    from plugins._chat_naming.api import chat_name

    agent = _Agent(
        [_Message({"user_message": "Run a report"}, sequence=1)], name="Old Task"
    )

    class _Scheduler:
        def __init__(self):
            self.updated = []

        async def reload(self):
            return None

        async def update_task(self, item_id, **kwargs):
            self.updated.append((item_id, kwargs))
            return SimpleNamespace(name=kwargs["name"])

    scheduler = _Scheduler()
    saved = []
    dirty = []
    monkeypatch.setattr(chat_name.AgentContext, "get", lambda _id: agent.context)
    monkeypatch.setattr(chat_name.TaskScheduler, "get", lambda: scheduler)
    monkeypatch.setattr(
        chat_name, "save_tmp_chat", lambda context: saved.append(context.name)
    )
    monkeypatch.setattr(
        chat_name, "mark_dirty_all", lambda *, reason: dirty.append(reason)
    )

    response = await object.__new__(chat_name.ChatName).process(
        {
            "action": "save",
            "kind": "task",
            "item_id": agent.context.id,
            "name": "Daily Report",
        },
        None,
    )

    assert response == {"ok": True, "name": "Daily Report"}
    assert scheduler.updated == [(agent.context.id, {"name": "Daily Report"})]
    assert agent.context.name == "Daily Report"
    assert saved == ["Daily Report"]
    assert dirty == ["plugins._chat_naming.save_task_name"]


async def test_chat_naming_endpoints_keep_default_auth_and_csrf_protection():
    from plugins._chat_naming.api.chat_name import ChatName

    assert ChatName.requires_auth() is True
    assert ChatName.requires_csrf() is True


@pytest.fixture
def naming_runtime(monkeypatch):
    contexts, persisted, dirty = {}, [], []
    monkeypatch.setattr(rename_chat.AgentContext, "get", lambda key: contexts.get(key))
    monkeypatch.setattr(
        naming.persist_chat,
        "save_tmp_chat",
        lambda context: persisted.append((context.id, context.name)),
    )
    monkeypatch.setattr(naming, "mark_dirty_all", lambda **kwargs: dirty.append(kwargs))
    monkeypatch.setattr(
        rename_chat.NotificationManager, "send_notification", lambda **kwargs: None
    )

    def make(key="chat", name=""):
        agent = _Agent(
            [_Message({"user_message": "Fix the parser"}, sequence=1)], name=name
        )
        agent.context.id = key
        agent.context.output_data = {}
        contexts[key] = agent.context
        return agent

    return SimpleNamespace(
        make=make, contexts=contexts, persisted=persisted, dirty=dirty
    )


async def test_background_naming_main_completes_and_persists(
    naming_runtime, monkeypatch
):
    agent = naming_runtime.make()
    gate, entered = asyncio.Event(), asyncio.Event()

    async def delayed(*args, **kwargs):
        entered.set()
        await gate.wait()
        return "Parser repair"

    monkeypatch.setattr(naming, "generate_name", delayed)
    await rename_chat.RenameChat(agent=agent).execute()
    task = rename_chat.TASKS[agent.context.id]
    await entered.wait()

    # A representative main operation completes while the provider is pending.
    async def main():
        return "main completed"

    assert await asyncio.wait_for(main(), 1) == "main completed"
    assert not task.done() and not naming_runtime.persisted
    gate.set()
    await task
    assert agent.context.name == "Parser repair"
    assert naming_runtime.persisted == [("chat", "Parser repair")]
    assert naming_runtime.dirty
    await asyncio.sleep(0)
    assert "chat" not in rename_chat.TASKS


async def test_once_mode_survives_second_message_and_deduplicates(
    naming_runtime, monkeypatch
):
    agent = naming_runtime.make()
    gate = asyncio.Event()
    calls = []

    async def delayed(*args, **kwargs):
        calls.append(kwargs["user_messages"])
        await gate.wait()
        return "First request"

    monkeypatch.setattr(naming, "generate_name", delayed)
    extension = rename_chat.RenameChat(agent=agent)
    await extension.execute()
    task = rename_chat.TASKS["chat"]
    await asyncio.sleep(0)
    agent.history._messages.append(
        _Message({"user_message": "Second request"}, sequence=2)
    )
    await extension.execute()
    assert rename_chat.TASKS["chat"] is task
    gate.set()
    await task
    assert agent.context.name == "First request" and len(calls) == 1


@pytest.mark.parametrize("deleted,manual", [(True, False), (False, True)])
async def test_late_result_cannot_rename_deleted_or_manual_chat(
    naming_runtime, monkeypatch, deleted, manual
):
    agent = naming_runtime.make(name="Original")
    gate, entered = asyncio.Event(), asyncio.Event()

    async def delayed(*args, **kwargs):
        entered.set()
        await gate.wait()
        return "Late title"

    monkeypatch.setattr(naming, "generate_name", delayed)
    monkeypatch.setattr(
        naming,
        "get_config",
        lambda agent: {"automatic_naming": True, "automatic_naming_mode": "always"},
    )
    await rename_chat.RenameChat(agent=agent).execute()
    task = rename_chat.TASKS["chat"]
    await entered.wait()
    if deleted:
        naming_runtime.contexts.clear()
    if manual:
        # Same text still changes revision: value comparison alone is insufficient.
        naming.save_context_name(agent, "Original")
    gate.set()
    await task
    assert agent.context.name == "Original"
    assert not any(name == "Late title" for _, name in naming_runtime.persisted)


async def test_always_mode_supersedes_and_retains_new_task(naming_runtime, monkeypatch):
    agent = naming_runtime.make()
    gate, entered = asyncio.Event(), asyncio.Event()

    async def delayed(*args, **kwargs):
        entered.set()
        await gate.wait()
        return "New title"

    monkeypatch.setattr(naming, "generate_name", delayed)
    monkeypatch.setattr(
        naming,
        "get_config",
        lambda agent: {"automatic_naming": True, "automatic_naming_mode": "always"},
    )
    extension = rename_chat.RenameChat(agent=agent)
    await extension.execute()
    old = rename_chat.TASKS["chat"]
    await entered.wait()
    await extension.execute()
    assert rename_chat.TASKS["chat"] is old  # same message does not duplicate
    agent.history._messages.append(_Message({"user_message": "New topic"}, sequence=2))
    await extension.execute()
    new = rename_chat.TASKS["chat"]
    assert new is not old
    with pytest.raises(asyncio.CancelledError):
        await old
    assert rename_chat.TASKS["chat"] is new
    gate.set()
    await new
    assert agent.context.name == "New title"


async def test_disabled_never_calls_provider(naming_runtime, monkeypatch):
    agent = naming_runtime.make()
    monkeypatch.setattr(
        naming,
        "get_config",
        lambda agent: {"automatic_naming": False, "automatic_naming_mode": "once"},
    )

    async def never(*args, **kwargs):
        pytest.fail("disabled naming must not call provider")

    monkeypatch.setattr(naming, "generate_name", never)
    await rename_chat.RenameChat(agent=agent).execute()
    assert "chat" not in rename_chat.TASKS or rename_chat.TASKS["chat"].done()


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError(),
        RuntimeError("provider private detail"),
        ValueError("invalid"),
        asyncio.CancelledError(),
    ],
)
async def test_failure_preserves_title_and_cleans_registry(
    naming_runtime, monkeypatch, failure
):
    agent = naming_runtime.make(name="Existing")
    monkeypatch.setattr(
        naming,
        "get_config",
        lambda agent: {"automatic_naming": True, "automatic_naming_mode": "always"},
    )

    async def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(naming, "generate_name", fail)
    await rename_chat.RenameChat(agent=agent).execute()
    task = rename_chat.TASKS["chat"]
    if isinstance(failure, asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        await task
    await asyncio.sleep(0)
    assert agent.context.name == "Existing"
    assert not naming_runtime.persisted and "chat" not in rename_chat.TASKS


async def test_concurrent_chats_have_independent_titles(naming_runtime, monkeypatch):
    agents = [naming_runtime.make(str(i)) for i in range(10)]

    async def generate(agent, **kwargs):
        await asyncio.sleep(0)
        return "Title " + agent.context.id

    monkeypatch.setattr(naming, "generate_name", generate)
    for agent in agents:
        await rename_chat.RenameChat(agent=agent).execute()
    await asyncio.gather(*(rename_chat.TASKS[a.context.id] for a in agents))
    assert [a.context.name for a in agents] == ["Title " + str(i) for i in range(10)]


@pytest.mark.parametrize("response", ["", " ", "{}", "```json\n{}\n```", None])
async def test_invalid_model_title_is_rejected(monkeypatch, response):
    agent = _Agent([_Message({"user_message": "Test"}, sequence=1)], response=response)
    monkeypatch.setattr(
        "plugins._model_config.helpers.model_config.get_utility_model_config",
        lambda agent: {"ctx_length": 1000},
    )
    with pytest.raises(ValueError):
        await naming.generate_name(agent)


async def test_total_provider_timeout_is_enforced(monkeypatch):
    agent = _Agent([_Message({"user_message": "Test"}, sequence=1)])
    cancelled = []

    async def slow(**kwargs):
        try:
            await asyncio.Future()
        finally:
            cancelled.append(True)

    agent.call_utility_model = slow
    monkeypatch.setattr(
        "plugins._model_config.helpers.model_config.get_utility_model_config",
        lambda agent: {"ctx_length": 1000},
    )
    monkeypatch.setattr(
        naming, "get_config", lambda agent: {"automatic_naming_timeout_seconds": 0.01}
    )
    with pytest.raises(TimeoutError):
        await naming.generate_name(agent)
    assert cancelled == [True]


@pytest.mark.parametrize(
    "value,expected",
    [
        (60000, 300),
        (-1, 1),
        ("bad", 45),
        (None, 45),
        (float("inf"), 45),
        (float("nan"), 45),
    ],
)
async def test_scoped_timeout_bounds(monkeypatch, value, expected):
    monkeypatch.setattr(
        naming.plugins,
        "get_plugin_config",
        lambda *args, **kwargs: {"automatic_naming_timeout_seconds": value},
    )
    assert naming.get_config(None)["automatic_naming_timeout_seconds"] == expected


async def test_framework_monologue_response_tool_finishes_before_naming(
    naming_runtime, monkeypatch
):
    from unittest.mock import AsyncMock
    from agent import AgentConfig, AgentContext
    from helpers import extension
    from helpers.llm_result import LLMResult
    from tools.response import ResponseTool

    # Exercise the real main loop and response-tool break path. Only model
    # boundaries, prompts and unrelated extensions are controlled by this test.
    monkeypatch.setattr(extension, "call_extensions_sync", lambda *args, **kwargs: None)
    context = AgentContext(
        AgentConfig(mcp_servers="", profile="agent0"),
        id="main-loop-naming",
        set_current=False,
    )
    naming_runtime.contexts[context.id] = context
    agent = context.agent0
    context.task = SimpleNamespace(is_alive=lambda: True)
    agent.history = _History([_Message({"user_message": "Fix parser"}, sequence=1)])
    agent.read_prompt = lambda name, **kwargs: f"{name}:{kwargs}"
    agent.prepare_prompt = AsyncMock(return_value=[])
    agent.call_chat_model_turn = AsyncMock(
        return_value=LLMResult(response="Main answer")
    )
    agent.handle_intervention = AsyncMock()
    agent.hist_add_ai_response = lambda *args, **kwargs: SimpleNamespace(id="assistant")
    agent.get_tool = lambda **kwargs: ResponseTool(
        agent, "response", None, kwargs["args"], "", None
    )
    gate, entered = asyncio.Event(), asyncio.Event()

    async def utility(**kwargs):
        entered.set()
        await gate.wait()
        return "Parser repair"

    agent.call_utility_model = utility
    monkeypatch.setattr(
        "plugins._model_config.helpers.model_config.get_utility_model_config",
        lambda agent: {"ctx_length": 1000},
    )

    async def hooks(point, agent=None, **kwargs):
        if point == "monologue_end":
            await rename_chat.RenameChat(agent=agent).execute()

    monkeypatch.setattr(extension, "call_extensions_async", hooks)
    try:
        assert await asyncio.wait_for(agent.monologue(), 1) == "Main answer"
        task = rename_chat.TASKS[context.id]
        await asyncio.wait_for(entered.wait(), 1)
        assert not task.done() and context.name is None
        gate.set()
        await task
        assert context.name == "Parser repair"
        assert (context.id, "Parser repair") in naming_runtime.persisted
    finally:
        gate.set()
        with AgentContext._contexts_lock:
            AgentContext._contexts.pop(context.id, None)
