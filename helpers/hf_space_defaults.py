import os
from helpers import dotenv
from helpers.print_style import PrintStyle

REQUIRED_PROFILES = {
    "developer",
    "hacker",
    "spynel",
    "reviewer",
    "tester",
    "tiny-coder",
    "debugger",
    "integrator",
    "frontend-qa",
    "evals",
    "shipper",
    "launch",
    "performance",
    "security",
    "refactorer",
    "maintainer",
    "data-engineer",
    "docs",
    "repository-manager",
}

REQUIRED_SKILLS = {
    "api-contract",
    "benchmark",
    "brag",
    "colab-execute",
    "compile-check",
    "context-packager",
    "dependency-doctor",
    "diff-self-review",
    "docker-diagnose",
    "failure-to-next-patch",
    "git-worktree",
    "github-pr",
    "golive",
    "hf-space",
    "patch-small",
    "playwright",
    "repo-map",
    "secret-safe-env",
    "spec-check",
    "symbol-locator",
    "task-slicer",
    "test-evidence",
    "test-targeted",
}


def assert_profiles_and_skills() -> None:
    """Verify that all required OpenOperator specialist profiles and skills exist and discover natively."""
    from helpers import subagents

    catalog = subagents.get_available_agents_dict(None)
    discovered_profiles = set(catalog.keys())
    missing_profiles = REQUIRED_PROFILES - discovered_profiles
    if missing_profiles:
        PrintStyle.error(f"OpenOperator profile discovery failed: missing profiles {sorted(missing_profiles)}")
        raise RuntimeError(f"OpenOperator profile assertion failed: missing profiles {sorted(missing_profiles)}")

    for profile_name in REQUIRED_PROFILES:
        try:
            agent_data = subagents.load_agent_data(profile_name)
            if not agent_data:
                raise ValueError(f"Profile {profile_name} returned empty data")
        except Exception as error:
            PrintStyle.error(f"OpenOperator profile load failed for {profile_name}: {error}")
            raise RuntimeError(f"OpenOperator profile load assertion failed for {profile_name}: {error}")

    from helpers import files
    skills_dir = files.get_abs_path("skills")
    existing_skills = set(files.get_subdirectories(skills_dir))
    missing_skills = REQUIRED_SKILLS - existing_skills
    if missing_skills:
        PrintStyle.error(f"OpenOperator skills assertion failed: missing skills {sorted(missing_skills)}")
        raise RuntimeError(f"OpenOperator skills assertion failed: missing skills {sorted(missing_skills)}")


def apply_hf_space_defaults() -> dict[str, bool]:
    """Apply only non-empty Space defaults and return a secret-free summary."""
    assert_profiles_and_skills()

    try:
        from helpers import runtime_secrets
        runtime_secrets.sync_runtime_secrets()
    except Exception:
        pass

    compatible_url = (
        os.environ.get("COMPATIBLE_URL", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_URL", "").strip()
    )
    compatible_model = (
        os.environ.get("COMPATIBLE_MODEL", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_MODEL", "").strip()
    )
    compatible_utility_url = (
        os.environ.get("COMPATIBLE_UTILITY_URL", "").strip()
        or os.environ.get("COMPATIBLE_UTILITY_BASE", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_UTILITY_URL", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_UTILITY_BASE", "").strip()
    )
    compatible_utility_model = (
        os.environ.get("COMPATIBLE_UTILITY_MODEL", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_UTILITY_MODEL", "").strip()
    )
    blablador_api_key = (
        os.environ.get("COMPATIBLE_API", "").strip()
        or os.environ.get("COMPATIBLE_API_KEY", "").strip()
        or os.environ.get("BLABLADOR_API_KEY", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_API", "").strip()
        or dotenv.get_dotenv_value("COMPATIBLE_API_KEY", "").strip()
        or dotenv.get_dotenv_value("BLABLADOR_API_KEY", "").strip()
        or dotenv.get_dotenv_value("API_KEY_OTHER", "").strip()
    )

    if not compatible_url: PrintStyle.warning("COMPATIBLE_URL is not configured")
    if not compatible_model: PrintStyle.warning("COMPATIBLE_MODEL is not configured")
    if not blablador_api_key: PrintStyle.warning("COMPATIBLE_API / BLABLADOR_API_KEY is not configured")
    if not (compatible_url or compatible_model or compatible_utility_url or compatible_utility_model or blablador_api_key):
        return {"url": False, "model": False, "api_key": False}

    if blablador_api_key:
        dotenv.save_dotenv_value("API_KEY_OTHER", blablador_api_key)
        dotenv.save_dotenv_value("COMPATIBLE_API", blablador_api_key)
        os.environ["API_KEY_OTHER"] = blablador_api_key
        os.environ["COMPATIBLE_API"] = blablador_api_key

    from plugins._model_config.helpers import model_config
    presets = model_config.get_presets()
    if not presets or not isinstance(presets, list):
        raise RuntimeError("Default model preset is unavailable")

    chat_slot = presets[0].setdefault("chat", {})
    if compatible_url or compatible_model:
        chat_slot["provider"] = "other"
    if compatible_url: chat_slot["api_base"] = compatible_url
    if compatible_model: chat_slot["name"] = compatible_model
    chat_slot.pop("api_key", None)

    if compatible_utility_url or compatible_utility_model:
        utility_slot = presets[0].setdefault("utility", {})
        utility_slot["provider"] = "other"
        if compatible_utility_url: utility_slot["api_base"] = compatible_utility_url
        if compatible_utility_model: utility_slot["name"] = compatible_utility_model
        utility_slot.pop("api_key", None)

    model_config.save_presets(presets)
    return {"url": bool(compatible_url or compatible_utility_url), "model": bool(compatible_model or compatible_utility_model), "api_key": bool(blablador_api_key)}


if __name__ == "__main__":
    apply_hf_space_defaults()
