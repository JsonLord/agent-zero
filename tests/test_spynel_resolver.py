import asyncio
from pathlib import Path

import pytest

from scripts.spynel_resolver import HTTPSClassifier, classify_ambiguous, resolve

PROFILES = {
    "developer": "Developer",
    "reviewer": "Reviewer",
    "tester": "Tester",
    "repository-manager": "Repository Manager",
    "prompt-improver": "Prompt Improver",
    "custom-agent": "My Specialist",
    "security": "Security",
}
EXTERNAL = {("sdk", "hermes"): "Hermes", ("external_agent", "remote"): "Remote"}

# Each row is a labeled decision; no live model or API key participates.
CASES = [
    ("@developer fix", "dispatch", "developer"),
    ("@reviewer inspect", "dispatch", "reviewer"),
    ("/hermes fix", "dispatch", "hermes"),
    ("@developer /hermes fix", "dispatch", "hermes"),
    ("@unknown fix", "abstain", None),
    ("/unknown fix", "abstain", None),
    ("Ask developer to fix nodepad.", "dispatch", "developer"),
    ("Have the reviewer inspect my code.", "dispatch", "reviewer"),
    ("Let prompt improver evaluate the system prompt.", "dispatch", "prompt-improver"),
    ("Tell repository manager to inspect GitHub.", "dispatch", "repository-manager"),
    ("Have the tester check journeytest-core.", "dispatch", "tester"),
    ("Use Hermes for this task.", "dispatch", "hermes"),
    ("Ask coding agent to fix this", "dispatch", "developer"),
    ("Tell repo manager to inspect", "dispatch", "repository-manager"),
    ("Have GEPA specialist evaluate", "dispatch", "prompt-improver"),
    ("Ask my specialist to work", "dispatch", "custom-agent"),
    ("Please ask the developer to fix", "dispatch", "developer"),
    ("USE HERMES for this", "dispatch", "hermes"),
    ("Delegate to security to audit", "dispatch", "security"),
    ("Use remote for this", "dispatch", "remote"),
    ("Ask custom-agent to fix", "dispatch", "custom-agent"),
    ("Let repository-manager inspect", "dispatch", "repository-manager"),
    ("Tell prompt_improver to inspect", "dispatch", "prompt-improver"),
    ("Work on the nodepad folder.", "local", None),
    ("Work on nodepad/src", "local", None),
    ("Inspect journeytest-core directory", "local", None),
    ("Work on experiments", "local", None),
    ("The developer said hello", "local", None),
    ("What is a reviewer?", "local", None),
    ("Explain SDK Hermes", "local", None),
    ("nodepad is interesting", "local", None),
    ('"Ask developer to fix"', "local", None),
    ("'Have reviewer inspect'", "local", None),
    ("`@developer fix`", "local", None),
    ("```\n@developer fix\n```", "local", None),
    ('Example: "Use Hermes for this"', "local", None),
    ("https://example.org/@developer", "local", None),
    ("https://example.org/hermes", "local", None),
    ("> @developer fix", "local", None),
    ("Ask developer.py to fix", "local", None),
    ("Use developer/src for code", "abstain", None),
    ("Have missing-agent fix this", "abstain", None),
    ("Use missing-sdk for this", "abstain", None),
    ("Ask developer and reviewer to inspect", "abstain", None),
    ("Use developer or reviewer", "abstain", None),
    ("@developer @reviewer inspect", "abstain", None),
    ("Use Hermes. Ask developer to fix", "abstain", None),
    ("Have reviewer inspect nodepad and experiments", "abstain", None),
    ("Have reviewer inspect missing-folder", "dispatch", "reviewer"),
    ("Ask developer to inspect ../escape", "dispatch", "developer"),
    ("Ask developer to inspect escaped", "dispatch", "developer"),
    ("Bitte den Reviewer fragen", "local", None),
    ("Demande au developer de corriger", "local", None),
    ("@reviewer проверка кода", "dispatch", "reviewer"),
    ("```\n@developer example", "local", None),
    ("Ask developer to fix and ask reviewer to inspect", "abstain", None),
    ("@developer\nfix this\n```python\nx = 1\n```", "dispatch", "developer"),
    (
        'Ask developer to fix nodepad\n\n```python\nprint("unchanged")\n```',
        "dispatch",
        "developer",
    ),
    ("Use developer2 for this", "abstain", None),
    ("Tell reviewer_backup to work", "abstain", None),
    ("Use repo manager to inspect", "dispatch", "repository-manager"),
    ("Let the tester inspect nodepad/src", "dispatch", "tester"),
]


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workdir"
    for path in ["nodepad/src", "journeytest-core", "experiments"]:
        (root / path).mkdir(parents=True)
    (tmp_path / "escape").mkdir()
    (root / "escaped").symlink_to(tmp_path / "escape", target_is_directory=True)
    return root


@pytest.mark.parametrize("text,decision,target", CASES)
def test_labeled_routes(workspace, text, decision, target):
    result = resolve(text, PROFILES, EXTERNAL, workspace)
    assert (result["decision"], result["target_id"]) == (decision, target)
    assert result["message"] == text
    if result["workspace_path"]:
        assert Path(result["workspace_path"]).is_relative_to(workspace)
        assert Path(result["workspace_path"]).is_dir()


@pytest.mark.parametrize(
    "folder", ["nodepad", "nodepad/src", "journeytest-core", "experiments"]
)
def test_workspace_canonical_paths(workspace, folder):
    result = resolve("Have reviewer inspect " + folder, PROFILES, EXTERNAL, workspace)
    # Nested child is the sole mentioned path; never silently choose its parent.
    assert result["workspace_path"] == str(workspace / folder)


def test_agent_folder_collision_and_title_collision(workspace):
    (workspace / "reviewer").mkdir()
    assert (
        resolve("Work on reviewer folder", PROFILES, EXTERNAL, workspace)["decision"]
        == "local"
    )
    collision = {**PROFILES, "other": "Reviewer"}
    result = resolve("Have reviewer inspect", collision, EXTERNAL, workspace)
    assert result["decision"] == "abstain" and result["ambiguous"]


@pytest.mark.asyncio
async def test_classifier_default_disabled_and_validated():
    candidates = [{"decision": "dispatch", "target_id": "reviewer"}]

    class Fake:
        calls = 0

        async def classify(self, *args):
            self.calls += 1
            return {"decision": "dispatch", "target_id": "attacker"}

    fake = Fake()
    assert await classify_ambiguous(fake, "text", candidates) == {"decision": "abstain"}
    assert fake.calls == 0
    assert await classify_ambiguous(fake, "text", candidates, enabled=True) == {
        "decision": "abstain"
    }

    async def valid(*args):
        return candidates[0]

    fake.classify = valid
    assert (
        await classify_ambiguous(fake, "text", candidates, enabled=True)
        == candidates[0]
    )


@pytest.mark.asyncio
async def test_classifier_timeout_and_cancellation():
    class Fake:
        async def classify(self, *args):
            raise TimeoutError()

    assert await classify_ambiguous(Fake(), "text", [{}], enabled=True) == {
        "decision": "abstain"
    }

    class Cancel:
        async def classify(self, *args):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await classify_ambiguous(Cancel(), "text", [{}], enabled=True)


@pytest.mark.parametrize(
    "url", ["http://example.org", "https://user:secret@example.org", "file:///tmp/x"]
)
def test_classifier_https_only(url):
    with pytest.raises(ValueError):
        HTTPSClassifier(url)
