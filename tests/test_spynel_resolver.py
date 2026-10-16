from pathlib import Path

import pytest

from scripts.spynel_resolver import discover, prepare_route, resolve

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


def test_no_classifier_interface_or_model_dependency():
    from scripts import spynel_resolver

    for name in ("Classifier", "HTTPSClassifier", "classify_ambiguous"):
        assert not hasattr(spynel_resolver, name)


def test_deterministic_routing_makes_no_network_calls(monkeypatch, workspace):
    import socket

    def never(*args, **kwargs):
        pytest.fail("routing must not make an inference/network request")

    monkeypatch.setattr(socket, "create_connection", never)
    for text, _, _ in CASES:
        prepare_route(text, PROFILES, EXTERNAL, workspace)


@pytest.mark.parametrize(
    "url", ["http://example.org", "https://user:secret@example.org", "file:///tmp/x"]
)
def test_registry_rejects_non_https_or_credentialed_endpoints(monkeypatch, url):
    monkeypatch.setenv("SPYNEL_SDK_UNTRUSTED_URL", url)
    _, external = discover()
    assert ("sdk", "untrusted") not in external


@pytest.mark.parametrize(
    "text,options,decision,target,path",
    [
        (
            "Have reviewer inspect nodepad/src/app.py",
            {},
            "dispatch",
            "reviewer",
            "nodepad/src",
        ),
        ("Have reviewer inspect file nodepad/missing.py", {}, "abstain", None, None),
        ("Have reviewer inspect folder missing", {}, "abstain", None, None),
        ("Have reviewer inspect missing-folder", {}, "abstain", None, None),
        ("Have reviewer inspect ../escape", {}, "abstain", None, None),
        ("Have reviewer inspect escaped", {}, "abstain", None, None),
        (
            "Work on nodepad",
            {"profile": "developer"},
            "dispatch",
            "developer",
            "nodepad",
        ),
        ("Improve the parser", {"profile": "invented"}, "abstain", None, None),
        ("Improve the parser", {"sdk": "unregistered"}, "abstain", None, None),
        (
            "Improve the parser",
            {"profile": "developer", "workspace": "missing"},
            "abstain",
            None,
            None,
        ),
        (
            "@reviewer inspect nodepad",
            {"profile": "developer"},
            "dispatch",
            "reviewer",
            "nodepad",
        ),
        (
            "Ask reviewer or developer to inspect nodepad",
            {"profile": "reviewer"},
            "abstain",
            None,
            None,
        ),
        ("/missing inspect nodepad", {"sdk": "hermes"}, "abstain", None, None),
        ('"@reviewer inspect"', {"profile": "reviewer"}, "abstain", None, None),
        (
            "https://example.org/@reviewer",
            {"profile": "reviewer"},
            "abstain",
            None,
            None,
        ),
        (
            "Ask developer to inspect www.example.org/@reviewer",
            {},
            "dispatch",
            "developer",
            None,
        ),
    ],
)
def test_final_dispatch_gate(workspace, text, options, decision, target, path):
    (workspace / "nodepad/src/app.py").write_text('print("test")\n')
    result = prepare_route(text, PROFILES, EXTERNAL, workspace, **options)
    assert result["decision"] == decision
    if decision == "dispatch":
        assert result["target_id"] == target
        assert result["workspace_path"] == (str(workspace / path) if path else None)
    if path is None:
        assert result["workspace_path"] is None


def test_folder_aliases_and_files_are_canonical(workspace):
    (workspace / "notepad").symlink_to(workspace / "nodepad", target_is_directory=True)
    (workspace / "nodepad/src/app.py").write_text("pass\n")
    for message, aliases in [
        ("Have reviewer inspect notepad", {}),
        ("Have reviewer inspect my project", {"my project": "nodepad"}),
        ('Have reviewer inspect folder "my project"', {"my project": "nodepad"}),
    ]:
        result = prepare_route(
            message, PROFILES, EXTERNAL, workspace, workspace_aliases=aliases
        )
        assert result["decision"] == "dispatch" and result["workspace_path"] == str(
            workspace / "nodepad"
        )
    result = prepare_route(
        "Have reviewer inspect nodepad/src/app.py", PROFILES, EXTERNAL, workspace
    )
    assert result["workspace_files"] == [str(workspace / "nodepad/src/app.py")]
    blocked = prepare_route(
        "Have reviewer inspect remote",
        PROFILES,
        EXTERNAL,
        workspace,
        workspace_aliases={"remote": "../escape"},
    )
    assert blocked["decision"] == "abstain" and blocked["reason"] == "workspace_escape"


def test_agent_folder_collision_does_not_invent_workspace(workspace):
    (workspace / "reviewer").mkdir()
    result = prepare_route(
        "Have reviewer inspect nodepad", PROFILES, EXTERNAL, workspace
    )
    assert result["decision"] == "dispatch" and result["workspace_path"] == str(
        workspace / "nodepad"
    )


def test_same_gateway_still_validates_accompanying_profile(workspace):
    result = prepare_route("@invented /hermes inspect", PROFILES, EXTERNAL, workspace)
    assert result["decision"] == "abstain" and result["reason"] == "unknown_profile"


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        '{"x": 1}',
        '{"": "nodepad"}',
        '{"my-project":"nodepad","my_project":"nodepad"}',
    ],
)
def test_trusted_alias_configuration_must_be_unambiguous(monkeypatch, raw):
    from scripts.spynel_resolver import load_workspace_aliases

    monkeypatch.setenv("SPYNEL_WORKSPACE_ALIASES", raw)
    with pytest.raises(ValueError):
        load_workspace_aliases()


def test_existing_main_selection_with_gateway_retains_validated_profile(workspace):
    result = prepare_route(
        "Improve the parser",
        PROFILES,
        EXTERNAL,
        workspace,
        profile="developer",
        sdk="hermes",
        workspace="nodepad",
    )
    assert result["decision"] == "dispatch"
    assert result["recognition"] == "validated_selection"
    assert result["target_type"] == "sdk" and result["target_id"] == "hermes"
    assert result["agent_profile"] == "developer"


def test_broken_folder_alias_never_authorizes_execution(workspace):
    (workspace / "broken").symlink_to(workspace / "missing", target_is_directory=True)
    result = prepare_route(
        "Have reviewer inspect broken", PROFILES, EXTERNAL, workspace
    )
    assert result["decision"] == "abstain" and result["reason"] == "workspace_missing"


def test_convenience_alias_tracks_registered_external_profile(workspace):
    registered = {("external_agent", "developer"): "Developer"}
    result = prepare_route(
        "Ask coding agent to inspect nodepad", PROFILES, registered, workspace
    )
    assert result["decision"] == "dispatch"
    assert (
        result["target_type"] == "external_agent" and result["target_id"] == "developer"
    )
