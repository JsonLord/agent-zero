import json
import os
import secrets
from python.helpers import files
from python.helpers.print_style import PrintStyle

def get_settings() -> dict:
    try:
        path = files.get_abs_path("settings.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        PrintStyle.error(f"Error loading settings: {e}")
    # Return defaults
    return {
        "chat_model_provider": "openai",
        "chat_model_name": "gpt-4",
        "chat_model_api_base": "",
        "chat_model_ctx_length": 128000,
        "chat_model_vision": True,
        "chat_model_rl_requests": 0,
        "chat_model_rl_input": 0,
        "chat_model_rl_output": 0,
        "chat_model_kwargs": {},
        "util_model_provider": "openai",
        "util_model_name": "gpt-4o-mini",
        "util_model_api_base": "",
        "util_model_ctx_length": 128000,
        "util_model_rl_requests": 0,
        "util_model_rl_input": 0,
        "util_model_rl_output": 0,
        "util_model_kwargs": {},
        "embed_model_provider": "openai",
        "embed_model_name": "text-embedding-3-small",
        "embed_model_api_base": "",
        "embed_model_rl_requests": 0,
        "embed_model_kwargs": {},
        "browser_model_provider": "openai",
        "browser_model_name": "gpt-4o-mini",
        "browser_model_api_base": "",
        "browser_model_vision": True,
        "browser_model_kwargs": {},
        "agent_profile": "default",
        "agent_memory_subdir": "default",
        "agent_knowledge_subdir": "custom",
        "mcp_servers": "",
        "rfc_url": "localhost",
        "rfc_port_http": 55521
    }

def save_settings(settings: dict) -> bool:
    try:
        path = files.get_abs_path("settings.json")
        with open(path, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        PrintStyle.error(f"Error saving settings: {e}")
        return False

def get_runtime_config(set):
    return {
        "code_exec_docker_enabled": False,
        "code_exec_ssh_enabled": False
    }

def create_auth_token():
    return secrets.token_hex(16)
