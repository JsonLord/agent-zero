from __future__ import annotations

import os
import stat
from pathlib import Path
from helpers import dotenv, files

SECRET_MAPPINGS = [
    ("HUGGINGFACE_TOKEN", ["HF_TOKEN"]),
    ("GITHUB_PAT", ["GH_TOKEN", "GITHUB_TOKEN"]),
    ("SPYNEL_AGENT_ZERO_API_KEY", ["SPYNEL_AGENT_ZERO_API_KEY"]),
]


def sync_runtime_secrets() -> dict[str, bool]:
    """Bridge process environment secrets to canonical runtime variables and usr/.env.

    Enforces 0600 permissions on usr/.env and secret rotation precedence:
      Space Secret Env > Canonical Explicit Env > Persisted usr/.env
    Returns a secret-free boolean status map.
    """
    env_file_path = Path(files.get_abs_path(dotenv.get_dotenv_file_path()))
    env_file_path.parent.mkdir(parents=True, exist_ok=True)

    status = {}

    for source_key, target_keys in SECRET_MAPPINGS:
        source_val = os.environ.get(source_key, "").strip()

        for target_key in target_keys:
            target_val = os.environ.get(target_key, "").strip()

            effective_val = source_val or target_val

            if effective_val:
                os.environ[target_key] = effective_val
                dotenv.save_dotenv_value(target_key, effective_val)
                status[target_key] = True
            else:
                persisted_val = dotenv.get_dotenv_value(target_key, "").strip()
                if persisted_val:
                    os.environ[target_key] = persisted_val
                    status[target_key] = True
                else:
                    status[target_key] = False

    if env_file_path.exists():
        try:
            env_file_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except OSError:
            pass

    return {
        "spynel_api_key": bool(os.environ.get("SPYNEL_AGENT_ZERO_API_KEY")),
        "hf_token": bool(os.environ.get("HF_TOKEN")),
        "github_token": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
    }


def get_secret_status() -> dict[str, bool]:
    """Return a secret-free boolean dictionary indicating configuration status."""
    return {
        "spynel_api_key": bool(os.environ.get("SPYNEL_AGENT_ZERO_API_KEY")),
        "hf_token": bool(os.environ.get("HF_TOKEN")),
        "github_token": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
    }
