from helpers import dotenv, runtime, settings
import os
import string
import random
import sys
from helpers.print_style import PrintStyle

# Space secrets (Hugging Face "Repository secrets", etc.) arrive as plain
# process environment variables. Map the ones we recognize into the app's own
# dotenv keys once, so they show up in Settings without a user having to
# retype them. Only applied when the target dotenv key is still unset, so a
# later manual change in the UI is never overwritten by a stale secret.
_SPACE_SECRET_DOTENV_MAP = {
    "AUTH_LOGIN": dotenv.KEY_AUTH_LOGIN,
    "AUTH_PASSWORD": dotenv.KEY_AUTH_PASSWORD,
    # "Other OpenAI compatible" provider slot (e.g. Blablador and similar
    # OpenAI-compatible inference endpoints have no dedicated provider entry).
    "BLABLADOR_API_KEY": "API_KEY_OTHER",
}


def _apply_space_secrets() -> None:
    for env_name, dotenv_key in _SPACE_SECRET_DOTENV_MAP.items():
        value = os.environ.get(env_name)
        if not value:
            continue
        if dotenv.get_dotenv_value(dotenv_key):
            continue
        dotenv.save_dotenv_value(dotenv_key, value)
        PrintStyle.standard(f"Applied {env_name} secret to {dotenv_key}.")


def _retire_legacy_collabora_runtime() -> None:
    if not any(arg.lower() == "--dockerized=true" for arg in sys.argv):
        return

    try:
        from plugins._office import hooks as office_hooks

        result = office_hooks.retire_collabora_web_runtime(force=True)
    except Exception as exc:
        PrintStyle.warning("Legacy Collabora runtime cleanup failed:", exc)
        return

    if result.get("errors"):
        PrintStyle.warning("Legacy Collabora runtime cleanup reported errors:", result["errors"])
    elif result.get("removed"):
        PrintStyle.info("Legacy Collabora runtime retired:", result)


PrintStyle.standard("Preparing environment...")

try:

    _retire_legacy_collabora_runtime()
    runtime.initialize()

    _apply_space_secrets()

    # generate random root password if not set (for SSH)
    root_pass = dotenv.get_dotenv_value(dotenv.KEY_ROOT_PASSWORD)
    if not root_pass:
        root_pass = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        PrintStyle.standard("Changing root password...")
    settings.set_root_password(root_pass)

except Exception as e:
    PrintStyle.error(f"Error in preload: {e}")
