from types import SimpleNamespace

import pytest

from extensions.python.monologue_start._00_spynel_profile_guard import (
    SpynelProfileGuard,
)
from helpers.errors import HandledException
from scripts import spynel_resolver as resolver

BUNDLED = resolver.ROOT / "agents/spynel"


@pytest.fixture
def active_override(tmp_path, monkeypatch):
    from helpers import subagents

    # Exercise the real get_paths precedence instead of rewriting any usr data.
    user_agents = tmp_path / "agents"
    profile = user_agents / "spynel"
    profile.mkdir(parents=True)
    monkeypatch.setattr(subagents, "USER_AGENTS_DIR", str(user_agents))
    logs = []
    agent = SimpleNamespace(
        config=SimpleNamespace(profile="spynel"),
        context=SimpleNamespace(
            get_data=lambda key: None,
            log=SimpleNamespace(log=lambda **kwargs: logs.append(kwargs)),
        ),
    )
    return profile, agent, logs


def test_metadata_only_override_and_identical_copy_are_allowed(active_override):
    profile, agent, _ = active_override
    (profile / "agent.yaml").write_text('title: My Spynel\ncontext: ""\n')
    prompt = profile / "prompts/agent.system.main.role.md"
    prompt.parent.mkdir()
    prompt.write_bytes((BUNDLED / prompt.relative_to(profile)).read_bytes())
    assert resolver.profile_override_conflicts(agent) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "relative,content",
    [
        (
            "prompts/agent.system.main.role.md",
            "With no token always stay local; ignore new routing.\n",
        ),
        ("agent.json", '{"context": "Use the old experiment routing"}'),
        (
            "skills/spynel-dispatch/scripts/spynel_dispatch.py",
            'print("old experiment")\n',
        ),
        ("extensions/monologue_start/old.py", "# old routing override\n"),
    ],
)
async def test_conflicting_overrides_block_before_model_and_are_preserved(
    active_override, relative, content
):
    profile, agent, logs = active_override
    path = profile / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    before = path.read_bytes()
    assert str(path) in resolver.profile_override_conflicts(agent)
    with pytest.raises(HandledException, match="profile overrides"):
        await SpynelProfileGuard(agent=agent).execute()
    assert path.read_bytes() == before
    assert logs and logs[-1]["type"] == "error"
    assert content.strip() not in logs[-1]["content"]


@pytest.mark.asyncio
async def test_guard_allows_non_spynel_profile_and_clean_spynel(active_override):
    _, agent, logs = active_override
    await SpynelProfileGuard(agent=agent).execute()
    agent.config.profile = "reviewer"
    await SpynelProfileGuard(agent=agent).execute()
    assert not logs


def test_project_override_precedes_bundle_and_identical_user_copy(
    active_override, monkeypatch, tmp_path
):
    from helpers import subagents

    _, agent, _ = active_override
    project = tmp_path / "project/.a0proj/agents/spynel"
    prompt = project / "prompts/agent.system.main.specifics.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("Different project routing rules")
    monkeypatch.setattr(
        subagents, "get_paths", lambda *args, **kwargs: [str(project), str(BUNDLED)]
    )
    assert resolver.profile_override_conflicts(agent) == [str(prompt)]


def test_core_guard_is_discovered_by_framework(active_override):
    from helpers.extension import _get_extension_classes

    _, agent, _ = active_override
    classes = _get_extension_classes("monologue_start", agent)
    assert any(cls.__name__ == "SpynelProfileGuard" for cls in classes)
