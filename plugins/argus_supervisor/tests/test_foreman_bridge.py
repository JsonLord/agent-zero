import ast
import inspect

import pytest

from plugins.argus_supervisor.helpers import foreman_bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("directive,hint", list(foreman_bridge.HINTS.items()))
async def test_bounded_foreman_directives_are_hints_only(
    setup, monkeypatch, directive, hint
):
    s, remote, _ = setup
    seen = {}

    async def invoke(*args, **kwargs):
        seen.update(args[2])
        return {"directive": directive}

    monkeypatch.setattr(foreman_bridge, "invoke", invoke)
    bridge = foreman_bridge.ForemanBridge(s.store.root / "foreman")
    result = await bridge.assess(
        s.store.load("campaign-1"), {"stdout": "evidence" * 10000}
    )
    assert result == {"directive": directive, "hint": hint}
    assert seen["evidence"]["trust"] == "UNTRUSTED_REMOTE_DATA"
    assert not remote.calls
    assert not hasattr(bridge, "client")
    imports = [
        n.module
        for n in ast.walk(ast.parse(inspect.getsource(foreman_bridge)))
        if isinstance(n, ast.ImportFrom)
    ]
    assert not any(x and ("a2a" in x or "heartbeat" in x) for x in imports)


@pytest.mark.asyncio
async def test_foreman_continue_skips_pure_evidence_wake(setup):
    s, remote, argus = setup

    class Foreman:
        async def assess(self, *args):
            return {"directive": "CONTINUE", "hint": "none"}

    s.foreman = Foreman()
    await s.tick()
    argus.calls.clear()
    metadata = remote.task["metadata"]["argus_supervisor"]
    metadata.update(revision="2", evidence_revision="e2")
    await s.tick()
    assert not argus.calls


@pytest.mark.asyncio
async def test_foreman_outage_does_not_block_terminal_review(setup):
    from plugins.argus_supervisor.helpers.models import SupervisorError

    s, remote, argus = setup

    class Foreman:
        async def assess(self, *args):
            raise SupervisorError("foreman_runtime_unavailable")

    s.foreman = Foreman()
    remote.task["status"]["state"] = "failed"
    await s.tick()
    assert len(argus.calls) == 1
