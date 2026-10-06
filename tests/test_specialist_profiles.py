from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = {"developer","hacker","spynel","reviewer","tester","tiny-coder","debugger","integrator","frontend-qa","evals","shipper","launch","performance","security","refactorer","maintainer","data-engineer","docs"}
SHARED = {"colab-execute","test-evidence","playwright","repo-map","spec-check","api-contract","benchmark","golive","brag","hf-space","git-worktree","github-pr","dependency-doctor","secret-safe-env","docker-diagnose","task-slicer","context-packager","symbol-locator","patch-small","compile-check","test-targeted","failure-to-next-patch","diff-self-review"}


def test_required_specialist_profiles_are_natively_discoverable(monkeypatch):
    fake_files = types.ModuleType("helpers.files")
    fake_files.get_abs_path = lambda *parts: str(ROOT.joinpath(*parts))
    fake_files.get_subdirectories = lambda directory: sorted(path.name for path in ROOT.joinpath(directory).iterdir() if path.is_dir())
    fake_files.exists = lambda path: Path(path).exists()
    fake_files.read_file = lambda path: Path(path).read_text()
    fake_files.read_text_files_in_dir = lambda directory, pattern="*.md": {
        path.name: path.read_text() for path in ROOT.joinpath(directory).glob(pattern)
    }
    fake_yaml = types.ModuleType("helpers.yaml")
    fake_yaml.loads = lambda text: {
        key.strip(): value.strip().lower() == "true" if value.strip().lower() in {"true", "false"} else value.strip()
        for key, value in (line.split(":", 1) for line in text.splitlines() if ":" in line)
    }
    fake_cache = types.ModuleType("helpers.cache"); fake_cache.toggle_area = lambda *args, **kwargs: None
    fake_plugins = types.ModuleType("helpers.plugins"); fake_plugins.get_enabled_plugin_paths = lambda *args, **kwargs: []
    fake_projects = types.ModuleType("helpers.projects"); fake_projects.load_project_subagents = lambda project: {}
    for name, module in {"helpers.files": fake_files, "helpers.yaml": fake_yaml, "helpers.cache": fake_cache, "helpers.plugins": fake_plugins, "helpers.projects": fake_projects}.items():
        monkeypatch.setitem(sys.modules, name, module)
    import helpers
    monkeypatch.setattr(helpers, "files", fake_files, raising=False); monkeypatch.setattr(helpers, "yaml", fake_yaml, raising=False); monkeypatch.setattr(helpers, "cache", fake_cache, raising=False)
    spec = importlib.util.spec_from_file_location("isolated_subagents", ROOT / "helpers/subagents.py")
    subagents = importlib.util.module_from_spec(spec); spec.loader.exec_module(subagents)
    profiles = subagents.get_available_agents_dict(None)
    assert REQUIRED <= profiles.keys()
    for name in REQUIRED - {"developer", "hacker", "spynel"}:
        loaded = subagents.load_agent_data(name)
        assert loaded.enabled is True
        assert loaded.prompts["agent.system.main.specifics.md"].strip()


def test_shared_skills_are_native_and_lazy():
    for name in SHARED:
        text = (ROOT / "skills" / name / "SKILL.md").read_text()
        assert text.startswith("---\nname:")
    golive = (ROOT / "skills/golive/SKILL.md").read_text()
    brag = (ROOT / "skills/brag/SKILL.md").read_text()
    assert "human approval" in golive and "Secrets never" in golive
    assert "lazily on invocation" in brag and "never install at startup" in brag


def test_orchestrators_contain_concrete_delegation_and_goal_policy():
    developer = (ROOT / "agents/developer/prompts/agent.system.main.specifics.md").read_text()
    hacker = (ROOT / "agents/hacker/prompts/agent.system.main.specifics.md").read_text()
    for token in ("@reviewer", "@tester", "@debugger", "@security", "/goal", "progress revision"):
        assert token in developer
    for token in ("@debugger", "@security", "@integrator", "@performance", "/goal"):
        assert token in hacker
    assert "uncontrolled shell-execution" in hacker


def test_colab_skill_reuses_actual_lifecycle_helper():
    skill = (ROOT / "skills/colab-execute/SKILL.md").read_text()
    helper = (ROOT / "scripts/colab_a0.py").read_text()
    assert "scripts/colab_a0.py" in skill
    for action in ("start", "health", "stop"):
        assert action in skill
        assert action in helper
