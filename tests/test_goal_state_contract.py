import asyncio
import importlib.util
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def goal_module(monkeypatch, tmp_path):
    fake_files = types.ModuleType("helpers.files")
    fake_files.USER_DIR = "usr"
    fake_files.PLUGINS_DIR = "plugins"
    fake_files.get_abs_path = lambda *parts: str(tmp_path.joinpath(*parts))
    fake_files.read_file = lambda path: Path(path).read_text()
    fake_tool = types.ModuleType("helpers.tool")

    class Response:
        def __init__(self, message, break_loop, additional=None):
            self.message = message
            self.break_loop = break_loop
            self.additional = additional

    class Tool:
        pass

    fake_tool.Response = Response
    fake_tool.Tool = Tool
    fake_agent = types.ModuleType("agent")
    fake_agent.AgentContext = types.SimpleNamespace(get=lambda context_id: None)
    fake_agent.UserMessage = lambda **values: values
    monkeypatch.setitem(sys.modules, "agent", fake_agent)
    monkeypatch.setitem(sys.modules, "helpers.files", fake_files)
    monkeypatch.setitem(sys.modules, "helpers.tool", fake_tool)
    import helpers

    monkeypatch.setattr(helpers, "files", fake_files, raising=False)
    spec = importlib.util.spec_from_file_location(
        "isolated_goal_state", ROOT / "plugins/_goal/tools/goal.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_notify_goal_changed", lambda context_id: None)
    return module


def test_goal_schema_persistence_revision_attention_and_completion(goal_module):
    g = goal_module
    current = g.create_goal(
        "ctx",
        "Deliver",
        owner_profile="developer",
        success_criteria=["tests", "live"],
        constraints=["no secrets"],
        autonomy={"level": "implementation"},
        idempotency_key="one",
        idempotency_scope="submission",
    )
    assert current["status"] == "active" and current["goal_id"].startswith("goal_")
    assert g.get_goal("ctx")["goal_id"] == current["goal_id"]
    assert (
        g.create_goal(
            "other", "duplicate", idempotency_key="one", idempotency_scope="submission"
        )["context_id"]
        == "ctx"
    )
    assert g.checkpoint_goal("ctx")["progress_revision"] == 1
    changed = g.checkpoint_goal(
        "ctx",
        milestone="tests",
        evidence=["pytest.xml"],
        requires_attention=True,
        attention_reason="approval_required",
    )
    assert changed["progress_revision"] == 2 and changed["requires_attention"]
    revised = g.revise_goal("ctx", constraints=["no secrets", "no PR"])
    assert revised["goal_revision"] == 2 and revised["history"][0]["revision"] == 1
    assert g.complete_goal("ctx")["status"] == "partially_verified"
    g.checkpoint_goal(
        "ctx",
        criterion_updates=[
            {"criterion": "tests", "state": "PASS"},
            {"criterion": "live", "state": "PASS"},
        ],
        requires_attention=False,
    )
    assert g.complete_goal("ctx")["status"] == "completed"


def test_goal_swarm_dependencies_context_isolation_and_failure(goal_module):
    g = goal_module
    parent = g.create_goal("parent", "Fix", success_criteria=["verified"])
    debug = g.create_goal(
        "debug",
        "Diagnose",
        parent_goal_id=parent["goal_id"],
        success_criteria=["diagnosed"],
    )
    security = g.create_goal("security", "Audit", parent_goal_id=parent["goal_id"])
    patch = g.create_goal(
        "patch",
        "Implement",
        parent_goal_id=parent["goal_id"],
        depends_on=[debug["goal_id"]],
        success_criteria=["implemented"],
    )
    tester = g.create_goal(
        "tester",
        "Test",
        parent_goal_id=parent["goal_id"],
        depends_on=[patch["goal_id"]],
    )
    reviewer = g.create_goal(
        "reviewer",
        "Review",
        parent_goal_id=parent["goal_id"],
        depends_on=[patch["goal_id"]],
    )
    assert debug["context_id"] != security["context_id"] and not g.dependencies_ready(
        patch
    )
    g.checkpoint_goal(
        "debug",
        criterion_updates=[
            {"criterion": "diagnosed", "state": "PASS", "evidence": ["trace"]}
        ],
    )
    g.complete_goal("debug", result={"evidence": ["trace"]})
    assert g.get_goal("patch")["status"] == "interrupted"
    g.checkpoint_goal(
        "patch", criterion_updates=[{"criterion": "implemented", "state": "PASS"}]
    )
    g.complete_goal("patch")
    assert (
        g.get_goal("tester")["status"]
        == g.get_goal("reviewer")["status"]
        == "interrupted"
    )
    failed = g.create_goal(
        "failed",
        "Fail",
        success_criteria=[
            {"criterion": "safe", "state": "FAIL", "evidence": ["finding"]}
        ],
    )
    assert g.complete_goal("failed")["status"] == "failed"


def test_checkpoint_revision_changes_only_for_semantic_progress(goal_module):
    goal_module.create_goal("ctx", "Deliver")

    first = goal_module.checkpoint_goal("ctx", milestone="testing", evidence=["pytest"])
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
    sibling = g.create_goal("sibling", "Sibling", parent_goal_id=parent_a["goal_id"])

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
    g.checkpoint_goal("ctx", criterion_updates=[{"criterion": "done", "state": "PASS"}])
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


def test_goal_startup_hook_runs_reconciliation(monkeypatch):
    calls = []
    fake_extension = types.ModuleType("helpers.extension")
    fake_extension.Extension = object
    fake_goal = types.ModuleType("plugins._goal.tools.goal")
    fake_goal.reconcile_persisted_goals = lambda: calls.append("reconciled") or []
    monkeypatch.setitem(sys.modules, "helpers.extension", fake_extension)
    monkeypatch.setitem(sys.modules, "plugins._goal.tools.goal", fake_goal)
    spec = importlib.util.spec_from_file_location(
        "isolated_goal_startup",
        ROOT
        / "plugins/_goal/extensions/python/startup_migration/_30_reconcile_goals.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.ReconcileGoals().execute() == []
    assert calls == ["reconciled"]


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


def test_explicit_recovery_moves_same_goal_to_fresh_context(goal_module, monkeypatch):
    g = goal_module
    original = g.create_goal(
        "lost-context",
        "Continue safely",
        owner_profile="developer",
        success_criteria=["tests pass"],
        autonomy={"level": "implementation"},
    )
    g.checkpoint_goal("lost-context", milestone="implementation", evidence=["patch"])
    g.reconcile_goal("lost-context", running=False)
    created = []

    class Context:
        def __init__(self, config, type):
            self.id = "fresh-context"
            self.running = False
            created.append(self)

        @staticmethod
        def get(context_id):
            return None

        def communicate(self, message):
            self.running = True

        def is_running(self):
            return self.running

    fake_agent = types.ModuleType("agent")
    fake_agent.AgentContext = Context
    fake_agent.AgentContextType = types.SimpleNamespace(USER="user")
    fake_agent.UserMessage = lambda **values: values
    fake_initialize = types.ModuleType("initialize")
    fake_initialize.initialize_agent = lambda override_settings=None: override_settings
    monkeypatch.setitem(sys.modules, "agent", fake_agent)
    monkeypatch.setitem(sys.modules, "initialize", fake_initialize)

    recovered = g.resume_goal("lost-context")

    assert recovered["goal_id"] == original["goal_id"]
    assert recovered["context_id"] == "fresh-context"
    assert recovered["success_criteria"] == original["success_criteria"]
    assert recovered["last_checkpoint"]["evidence"] == ["patch"]
    assert recovered["history"][-1]["event"] == "context_recovered"
    assert recovered["status"] == "active"
    assert g.get_goal("lost-context") is None
    assert g.get_goal("fresh-context")["goal_id"] == original["goal_id"]
    assert len(created) == 1


def test_operational_goal_recovery_requires_approval(goal_module, monkeypatch):
    g = goal_module
    current = g.create_goal(
        "shipper-lost",
        "Deploy",
        owner_profile="shipper",
        autonomy={"level": "operational"},
    )
    g.reconcile_goal("shipper-lost", running=False)

    recovered = g.recover_goal_context(current["goal_id"])

    assert recovered["context_id"] == "shipper-lost"
    assert recovered["status"] == "interrupted"
    assert recovered["requires_attention"] is True
    assert recovered["attention_reason"] == "approval_required"


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


@pytest.mark.parametrize("iteration", range(5))
def test_stress_fifty_concurrent_checkpoints(goal_module, iteration):
    g = goal_module
    context_id = f"stress-checkpoints-{iteration}"
    g.create_goal(context_id, "Stress revisions")
    barrier = threading.Barrier(50)
    failures = []

    def mutate(index):
        try:
            barrier.wait()
            g.checkpoint_goal(context_id, milestone=f"semantic-{index}")
        except BaseException as error:
            failures.append(error)

    threads = [threading.Thread(target=mutate, args=(index,)) for index in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert failures == []
    assert all(not thread.is_alive() for thread in threads)
    assert g.get_goal(context_id)["progress_revision"] == 51
    assert len(list(g._goals_directory().glob("*.json"))) == 1


@pytest.mark.parametrize("iteration", range(5))
def test_stress_twenty_goal_contexts_remain_isolated(goal_module, iteration):
    g = goal_module
    contexts = [f"mixed-{iteration}-{index}" for index in range(20)]
    for context_id in contexts:
        g.create_goal(context_id, f"Objective {context_id}", success_criteria=["done"])

    def mutate(index):
        context_id = contexts[index]
        g.checkpoint_goal(context_id, milestone=f"only-{context_id}")
        operation = index % 5
        if operation == 0:
            g.update_goal(context_id, status="paused")
        elif operation == 1:
            g.update_goal(context_id, status="blocked")
        elif operation == 2:
            g.update_goal(context_id, status="interrupted")
        elif operation == 3:
            g.update_goal(context_id, status="cancelled")
        else:
            g.checkpoint_goal(
                context_id, criterion_updates=[{"criterion": "done", "state": "PASS"}]
            )
            g.complete_goal(context_id)

    threads = [threading.Thread(target=mutate, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    for index, context_id in enumerate(contexts):
        item = g.get_goal(context_id)
        assert item["objective"] == f"Objective {context_id}"
        assert item["current_milestone"] == f"only-{context_id}"
        assert (
            item["status"]
            == ["paused", "blocked", "interrupted", "cancelled", "completed"][index % 5]
        )


@pytest.mark.parametrize("iteration", range(5))
def test_stress_duplicate_submission_is_exactly_once(goal_module, iteration):
    g = goal_module
    barrier = threading.Barrier(30)
    identities = []

    def submit(index):
        barrier.wait()
        item = g.create_goal(
            f"storm-{iteration}-{index}",
            "Same text",
            idempotency_key="same-request",
            idempotency_scope=f"storm-{iteration}",
        )
        identities.append((item["goal_id"], item["context_id"]))

    threads = [threading.Thread(target=submit, args=(index,)) for index in range(30)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(set(identities)) == 1
    assert len(g._all_goals()) == 1
    independent = g.create_goal(
        f"storm-independent-{iteration}",
        "Same text",
        idempotency_key="different-request",
        idempotency_scope=f"storm-{iteration}",
    )
    assert independent["goal_id"] != identities[0][0]


def test_corrupted_goal_files_are_bounded_and_skipped(goal_module):
    g = goal_module
    valid = g.create_goal("valid", "Valid")
    directory = g._goals_directory()
    (directory / "truncated.json").write_text('{"goal_id":', encoding="utf-8")
    (directory / "invalid.json").write_text("not-json", encoding="utf-8")
    (directory / "missing.json").write_text('{"unrelated": true}', encoding="utf-8")

    assert [item["goal_id"] for item in g._all_goals()] == [valid["goal_id"]]


def test_resource_limit_rejection_leaves_no_ghost_goals(goal_module, monkeypatch):
    g = goal_module
    monkeypatch.setattr(g, "MAX_CHILD_GOALS", 2)
    parent = g.create_goal("parent-limit", "Parent")
    g.create_goal("child-one", "One", parent_goal_id=parent["goal_id"])
    g.create_goal("child-two", "Two", parent_goal_id=parent["goal_id"])

    with pytest.raises(ValueError, match="Maximum child goals"):
        g.create_goal("ghost", "Ghost", parent_goal_id=parent["goal_id"])

    assert g.get_goal("ghost") is None
    assert len(g.list_child_goals(parent["goal_id"])) == 2


def test_depth_and_concurrency_limit_boundaries(goal_module, monkeypatch):
    g = goal_module
    monkeypatch.setattr(g, "MAX_GOAL_DEPTH", 2)
    root = g.create_goal("depth-root", "Root")
    child = g.create_goal("depth-child", "Child", parent_goal_id=root["goal_id"])
    grandchild = g.create_goal(
        "depth-grandchild", "Grandchild", parent_goal_id=child["goal_id"]
    )
    assert grandchild["depth"] == 2
    with pytest.raises(ValueError, match="Maximum goal depth"):
        g.create_goal("depth-ghost", "Too deep", parent_goal_id=grandchild["goal_id"])
    assert g.get_goal("depth-ghost") is None

    # Use a separate isolated store view after finalizing the depth children.
    for context_id in ("depth-child", "depth-grandchild"):
        g.update_goal(context_id, status="cancelled")
    monkeypatch.setattr(g, "MAX_CONCURRENT_GOALS", 2)
    concurrent_parent = g.create_goal("concurrent-parent", "Concurrent parent")
    g.create_goal("worker-one", "One", parent_goal_id=concurrent_parent["goal_id"])
    g.create_goal("worker-two", "Two", parent_goal_id=concurrent_parent["goal_id"])
    with pytest.raises(ValueError, match="Maximum concurrent"):
        g.create_goal(
            "worker-ghost", "Three", parent_goal_id=concurrent_parent["goal_id"]
        )
    assert g.get_goal("worker-ghost") is None


@pytest.mark.parametrize("iteration", range(5))
def test_swarm_dag_stress_respects_dependencies_and_failure(
    goal_module, monkeypatch, iteration
):
    g = goal_module
    monkeypatch.setattr(g, "MAX_CHILD_GOALS", 30)
    monkeypatch.setattr(g, "MAX_CONCURRENT_GOALS", 30)
    parent = g.create_goal(
        f"dag-parent-{iteration}", "DAG", success_criteria=["all done"]
    )
    roots = [
        g.create_goal(
            f"dag-{iteration}-root-{index}",
            f"Root {index}",
            parent_goal_id=parent["goal_id"],
            success_criteria=["done"],
        )
        for index in range(5)
    ]
    joins = [
        g.create_goal(
            f"dag-{iteration}-join-{index}",
            f"Join {index}",
            parent_goal_id=parent["goal_id"],
            depends_on=[roots[index]["goal_id"], roots[(index + 1) % 5]["goal_id"]],
            success_criteria=["done"],
        )
        for index in range(5)
    ]
    finals = [
        g.create_goal(
            f"dag-{iteration}-final-{index}",
            f"Final {index}",
            parent_goal_id=parent["goal_id"],
            depends_on=[joins[index]["goal_id"]],
            success_criteria=["done"],
        )
        for index in range(5)
    ]
    blocked = g.create_goal(
        f"dag-{iteration}-blocked",
        "Blocked",
        parent_goal_id=parent["goal_id"],
        depends_on=[roots[0]["goal_id"]],
    )
    failed = g.create_goal(
        f"dag-{iteration}-failed",
        "Failed",
        parent_goal_id=parent["goal_id"],
        success_criteria=[{"criterion": "safe", "state": "FAIL"}],
    )
    failure_dependent = g.create_goal(
        f"dag-{iteration}-failure-dependent",
        "Must wait forever",
        parent_goal_id=parent["goal_id"],
        depends_on=[failed["goal_id"]],
    )
    extras = [
        g.create_goal(
            f"dag-{iteration}-extra-{index}",
            f"Extra {index}",
            parent_goal_id=parent["goal_id"],
            success_criteria=["done"],
        )
        for index in range(2)
    ]
    assert len(g.list_child_goals(parent["goal_id"])) == 20
    assert all(
        g.get_goal(item["context_id"])["status"] == "pending" for item in joins + finals
    )

    for item in roots + extras:
        g.checkpoint_goal(
            item["context_id"],
            criterion_updates=[{"criterion": "done", "state": "PASS"}],
        )
        g.complete_goal(item["context_id"])
    g.complete_goal(failed["context_id"])
    g.update_goal(blocked["context_id"], status="blocked")

    assert all(g.dependencies_ready(g.get_goal(item["context_id"])) for item in joins)
    assert all(
        g.get_goal(item["context_id"])["status"] == "interrupted" for item in joins
    )
    assert all(g.get_goal(item["context_id"])["status"] == "pending" for item in finals)
    assert g.get_goal(failure_dependent["context_id"])["status"] == "pending"
    assert g.complete_goal(parent["context_id"])["status"] == "partially_verified"
