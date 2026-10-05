import importlib.util
import sys
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
    current=g.create_goal("ctx","Deliver",owner_profile="developer",success_criteria=["tests","live"],constraints=["no secrets"],autonomy={"level":"implementation"},idempotency_key="one")
    assert current["status"]=="active" and current["goal_id"].startswith("goal_")
    assert g.get_goal("ctx")["goal_id"]==current["goal_id"]
    assert g.create_goal("other","duplicate",idempotency_key="one")["context_id"]=="ctx"
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
    debug=g.create_goal("debug","Diagnose",parent_goal_id=parent["goal_id"])
    security=g.create_goal("security","Audit",parent_goal_id=parent["goal_id"])
    patch=g.create_goal("patch","Implement",parent_goal_id=parent["goal_id"],depends_on=[debug["goal_id"]])
    tester=g.create_goal("tester","Test",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    reviewer=g.create_goal("reviewer","Review",parent_goal_id=parent["goal_id"],depends_on=[patch["goal_id"]])
    for item in (patch,tester,reviewer): g.update_goal(item["context_id"],status="pending")
    assert debug["context_id"]!=security["context_id"] and not g.dependencies_ready(patch)
    g.complete_goal("debug",result={"evidence":["trace"]})
    assert g.get_goal("patch")["status"]=="active"
    g.complete_goal("patch")
    assert g.get_goal("tester")["status"]==g.get_goal("reviewer")["status"]=="active"
    failed=g.create_goal("failed","Fail",success_criteria=[{"criterion":"safe","state":"FAIL","evidence":["finding"]}])
    assert g.complete_goal("failed")["status"]=="failed"
