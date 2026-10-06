import asyncio
import importlib.util
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture()
def goal_module(monkeypatch,tmp_path):
    fake_files=types.ModuleType("helpers.files")
    fake_files.USER_DIR="usr"; fake_files.PLUGINS_DIR="plugins"
    fake_files.get_abs_path=lambda *parts:str(tmp_path.joinpath(*parts))
    fake_files.read_file=lambda path:Path(path).read_text()
    fake_tool=types.ModuleType("helpers.tool")
    class Response:
        def __init__(self,message,break_loop,additional=None): self.message=message; self.break_loop=break_loop; self.additional=additional
    class Tool: pass
    fake_tool.Response=Response; fake_tool.Tool=Tool
    monkeypatch.setitem(sys.modules,"helpers.files",fake_files)
    monkeypatch.setitem(sys.modules,"helpers.tool",fake_tool)
    import helpers
    monkeypatch.setattr(helpers,"files",fake_files,raising=False)
    spec=importlib.util.spec_from_file_location("isolated_goal_state",ROOT/"plugins/_goal/tools/goal.py")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module,"_notify_goal_changed",lambda context_id:None)
    return module


def test_goal_schema_persistence_revision_attention_and_completion(goal_module):
    g=goal_module
    current=g.create_goal("ctx","Deliver",owner_profile="developer",success_criteria=["tests","live"],constraints=["no secrets"],autonomy={"level":"implementation"},idempotency_key="one",idempotency_scope="submission")
    assert current["status"]=="active" and current["goal_id"].startswith("goal_")
    assert g.get_goal("ctx")["goal_id"]==current["goal_id"]
    assert g.create_goal("other","duplicate",idempotency_key="one",idempotency_scope="submission")["context_id"]=="ctx"
    assert g.checkpoint_goal("ctx")["progress_revision"]==1
    changed=g.checkpoint_goal("ctx",milestone="tests",evidence=["pytest.xml"],requires_attention=True,attention_reason="approval_required")
    assert changed["progress_revision"]==2 and changed["requires_attention"]
    revised=g.revise_goal("ctx",constraints=["no secrets","no PR"])
    assert revised["goal_revision"]==2 and revised["history"][0]["revision"]==1
    assert g.complete_goal("ctx")["status"]=="partially_verified"
    g.checkpoint_goal("ctx",criterion_updates=[{"criterion":"tests","state":"PASS"},{"criterion":"live","state":"PASS"}],requires_attention=False)
    assert g.complete_goal("ctx")["status"]=="completed"


def test_goal_swarm_dependencies_context_isolation_and_failure(goal_module):
    g=goal_module
    parent=g.create_goal("parent","Fix",success_criteria=["verified"])
    debug=g.create_goal("debug","Diagnose",parent_goal_id=parent["goal_id"],success_criteria=["diagnosed"])
    security=g.create_goal("security","Audit",parent_goal_id=parent["goal_id"])
    patch=g.create_goal("patch","Implement",parent_goal_id=parent["goal_id"],depends_on=[debug["goal_id"]],success_criteria=["implemented"])
    tester=g.create_goal("tester","Test",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    reviewer=g.create_goal("reviewer","Review",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    assert debug["context_id"]!=security["context_id"] and not g.dependencies_ready(patch)
    g.checkpoint_goal("debug",criterion_updates=[{"criterion":"diagnosed","state":"PASS","evidence":["trace"]}])
    g.complete_goal("debug",result={"evidence":["trace"]})
    assert g.get_goal("patch")["status"]=="interrupted"
    g.checkpoint_goal("patch",criterion_updates=[{"criterion":"implemented","state":"PASS"}])
    g.complete_goal("patch")
    assert g.get_goal("tester")["status"]==g.get_goal("reviewer")["status"]=="interrupted"
    failed=g.create_goal("failed","Fail",success_criteria=[{"criterion":"safe","state":"FAIL","evidence":["finding"]}])
    assert g.complete_goal("failed")["status"]=="failed"


def test_checkpoint_revision_changes_only_for_semantic_progress(goal_module):
    goal_module.create_goal("ctx", "Deliver")

    first = goal_module.checkpoint_goal(
        "ctx", milestone="testing", evidence=["pytest"]
    )
    revision = first["progress_revision"]
    repeated = goal_module.checkpoint_goal(
        "ctx", milestone="testing", evidence=["pytest"]
    )
    changed = goal_module.checkpoint_goal(
        "ctx", milestone="testing", evidence=["pytest", "coverage"]
    )

    assert repeated["progress_revision"] == revision
    assert changed["progress_revision"] == revision + 1


def test_dependency_validation_rejects_missing_self_cross_parent_and_cycle(goal_module):
    g = goal_module
    parent_a = g.create_goal("parent-a", "Parent A")
    parent_b = g.create_goal("parent-b", "Parent B")
    sibling = g.create_goal(
        "sibling", "Sibling", parent_goal_id=parent_a["goal_id"]
    )

    with pytest.raises(ValueError, match="[Dd]ependenc"):
        g.create_goal(
            "missing",
            "Missing dependency",
            parent_goal_id=parent_a["goal_id"],
            depends_on=["goal_missing"],
        )
    with pytest.raises(ValueError, match="[Dd]ependenc"):
        g.create_goal(
            "cross-parent",
            "Cross parent",
            parent_goal_id=parent_b["goal_id"],
            depends_on=[sibling["goal_id"]],
        )

    proposed_id = "goal_proposed"
    with pytest.raises(ValueError, match="itself|self"):
        g._validate_dependencies(
            goal_id=proposed_id,
            parent_goal_id=parent_a["goal_id"],
            depends_on=[proposed_id],
        )

    # A malformed historic edge must not permit a new edge that closes a cycle.
    sibling["depends_on"] = [proposed_id]
    g._write_goal(sibling)
    with pytest.raises(ValueError, match="cycle"):
        g._validate_dependencies(
            goal_id=proposed_id,
            parent_goal_id=parent_a["goal_id"],
            depends_on=[sibling["goal_id"]],
        )


def test_valid_multiple_sibling_dependencies(goal_module):
    g = goal_module
    parent = g.create_goal("parent", "Parent")
    first = g.create_goal("first", "First", parent_goal_id=parent["goal_id"])
    second = g.create_goal("second", "Second", parent_goal_id=parent["goal_id"])

    child = g.create_goal(
        "child",
        "Child",
        parent_goal_id=parent["goal_id"],
        depends_on=[first["goal_id"], second["goal_id"]],
    )

    assert child["depends_on"] == [first["goal_id"], second["goal_id"]]
    assert child["status"] == "pending"


def test_idempotency_is_scoped_to_submission_identity(goal_module):
    g = goal_module
    first = g.create_goal(
        "ctx-a",
        "Inspect release",
        idempotency_key="request-1",
        idempotency_scope="project-a",
    )
    retry = g.create_goal(
        "ctx-retry",
        "Inspect release",
        idempotency_key="request-1",
        idempotency_scope="project-a",
    )
    independent_request = g.create_goal(
        "ctx-b",
        "Inspect release",
        idempotency_key="request-2",
        idempotency_scope="project-a",
    )
    independent_parent = g.create_goal(
        "ctx-c",
        "Inspect release",
        idempotency_key="request-1",
        idempotency_scope="project-b",
    )

    assert retry["goal_id"] == first["goal_id"]
    assert independent_request["goal_id"] != first["goal_id"]
    assert independent_parent["goal_id"] != first["goal_id"]


def test_concurrent_semantic_updates_do_not_lose_revisions(goal_module):
    g = goal_module
    g.create_goal("ctx", "Concurrent updates")
    worker_count = 12
    barrier = threading.Barrier(worker_count)
    failures: list[BaseException] = []

    def checkpoint(index: int) -> None:
        try:
            barrier.wait()
            g.checkpoint_goal("ctx", milestone=f"worker-{index}")
        except BaseException as error:  # pragma: no cover - assertion reports details
            failures.append(error)

    threads = [
        threading.Thread(target=checkpoint, args=(index,))
        for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert failures == []
    assert all(not thread.is_alive() for thread in threads)
    assert g.get_goal("ctx")["progress_revision"] == 1 + worker_count


def test_completion_without_criteria_is_not_falsely_verified(goal_module):
    goal_module.create_goal("ctx", "Legacy goal without criteria")

    completed = goal_module.complete_goal("ctx", result={"evidence": ["note"]})

    assert completed["status"] == "partially_verified"
    assert completed["requires_attention"] is True
    assert completed["attention_reason"] == "manual_action_required"


def test_parent_completion_waits_for_nonfinal_children(goal_module):
    g = goal_module
    parent = g.create_goal("parent", "Parent", success_criteria=["done"])
    child = g.create_goal(
        "child", "Child", parent_goal_id=parent["goal_id"], success_criteria=["done"]
    )
    g.checkpoint_goal(
        "parent", criterion_updates=[{"criterion": "done", "state": "PASS"}]
    )

    waiting = g.complete_goal("parent")
    assert waiting["status"] == "partially_verified"
    assert waiting["requires_attention"] is True

    g.checkpoint_goal(
        "child", criterion_updates=[{"criterion": "done", "state": "PASS"}]
    )
    assert g.complete_goal("child")["status"] == "completed"
    assert g.complete_goal("parent")["status"] == "completed"


def test_state_machine_rejects_implicit_reopen_of_final_goal(goal_module):
    g = goal_module
    g.create_goal("ctx", "Final", success_criteria=["done"])
    g.checkpoint_goal(
        "ctx", criterion_updates=[{"criterion": "done", "state": "PASS"}]
    )
    assert g.complete_goal("ctx")["status"] == "completed"

    with pytest.raises(ValueError, match="transition|final|resume"):
        g.update_goal("ctx", status="active")


def test_restart_reconciliation_never_leaves_missing_worker_active(
    goal_module, monkeypatch
):
    g = goal_module
    g.create_goal("active", "Was running")
    g.create_goal("done", "Already done", success_criteria=["done"])
    g.checkpoint_goal(
        "done", criterion_updates=[{"criterion": "done", "state": "PASS"}]
    )
    g.complete_goal("done")

    fake_agent = types.ModuleType("agent")
    fake_agent.AgentContext = types.SimpleNamespace(get=lambda _context_id: None)
    monkeypatch.setitem(sys.modules, "agent", fake_agent)
    reconciled = g.reconcile_persisted_goals()

    assert g.get_goal("active")["status"] == "interrupted"
    assert g.get_goal("active")["requires_attention"] is True
    assert g.get_goal("done")["status"] == "completed"
    assert {item["context_id"] for item in reconciled} == {"active"}


def test_resume_is_dependency_aware_idempotent_and_rejects_final_states(
    goal_module, monkeypatch
):
    g = goal_module
    parent = g.create_goal("parent", "Parent")
    dependency = g.create_goal(
        "dependency",
        "Dependency",
        parent_goal_id=parent["goal_id"],
        success_criteria=["done"],
    )
    child = g.create_goal(
        "child",
        "Child",
        parent_goal_id=parent["goal_id"],
        depends_on=[dependency["goal_id"]],
    )
    calls = []

    class Context:
        paused = True
        running = False

        def is_running(self):
            return self.running

        def communicate(self, message):
            calls.append(message)
            self.running = True

    context = Context()
    fake_agent = types.ModuleType("agent")
    fake_agent.AgentContext = types.SimpleNamespace(
        get=lambda context_id: context if context_id == "child" else None
    )
    fake_agent.UserMessage = lambda **values: values
    monkeypatch.setitem(sys.modules, "agent", fake_agent)

    waiting = g.resume_goal("child")
    assert waiting["status"] == "pending"
    assert calls == []

    g.checkpoint_goal(
        "dependency", criterion_updates=[{"criterion": "done", "state": "PASS"}]
    )
    g.complete_goal("dependency")
    resumed = g.resume_goal("child")
    assert resumed["status"] == "active"
    assert len(calls) == 1
    assert context.paused is False

    repeated = g.resume_goal("child")
    assert repeated["status"] == "active"
    assert len(calls) == 1

    g.update_goal("child", status="cancelled")
    with pytest.raises(ValueError, match="cancelled|final|resume"):
        g.resume_goal("child")


@pytest.mark.parametrize(
    ("goal_status", "running", "task_attached", "expected"),
    [
        ("active", False, False, "interrupted"),
        ("active", False, True, "interrupted"),
        ("active", True, True, "working"),
        ("completed", False, True, "completed"),
    ],
)
def test_api_poll_reconciles_stopped_goal_workers(
    goal_module,
    monkeypatch,
    goal_status,
    running,
    task_attached,
    expected,
):
    context_id = f"poll-{goal_status}-{running}-{task_attached}"
    goal_module.create_goal(context_id, "Poll lifecycle", success_criteria=["done"])
    if goal_status == "completed":
        goal_module.checkpoint_goal(
            context_id,
            criterion_updates=[{"criterion": "done", "state": "PASS"}],
        )
        goal_module.complete_goal(context_id)

    class Output:
        items = []
        end = 0

    class Log:
        progress = 0

        @staticmethod
        def output(start=0):
            return Output()

    class Task:
        @staticmethod
        def is_ready():
            return True

        @staticmethod
        def result_sync(timeout=0):
            return "worker result"

    context = types.SimpleNamespace(
        id=context_id,
        log=Log(),
        task=Task() if task_attached else None,
        is_running=lambda: running,
    )
    fake_agent = types.ModuleType("agent")
    fake_agent.AgentContext = types.SimpleNamespace(get=lambda _context_id: context)
    fake_api = types.ModuleType("helpers.api")
    fake_api.ApiHandler = object
    fake_api.Request = object

    class HttpResponse:
        def __init__(self, message, status=200):
            self.message = message
            self.status_code = status

    fake_api.Response = HttpResponse
    monkeypatch.setitem(sys.modules, "agent", fake_agent)
    monkeypatch.setitem(sys.modules, "helpers.api", fake_api)
    monkeypatch.setitem(sys.modules, "plugins._goal.tools.goal", goal_module)
    spec = importlib.util.spec_from_file_location(
        f"isolated_api_poll_{context_id}", ROOT / "api/api_poll.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    response = asyncio.run(
        object.__new__(module.ApiPoll).process({"context_id": context_id}, None)
    )

    assert response["status"] == expected
    assert response["running"] is running
