import os

from helpers import dotenv, plugins
from helpers.extension import Extension
from helpers.print_style import PrintStyle
from plugins._model_config.helpers import model_config


PRESET_NAME = "Tiny Coder Environment"


class TinyCoderEnvironment(Extension):
    """Bind tiny-coder to an optional secret-free environment preset."""

    def execute(self, **kwargs):
        provider = os.environ.get("TINY_CODER_PROVIDER", "").strip()
        model = os.environ.get("TINY_CODER_MODEL", "").strip()
        api_base = os.environ.get("TINY_CODER_API_BASE", "").strip()
        api_key = os.environ.get("TINY_CODER_API_KEY", "").strip()
        if not any((provider, model, api_base, api_key)):
            return "inherited"
        if not provider or not model:
            PrintStyle.warning(
                "Tiny Coder override requires TINY_CODER_PROVIDER and TINY_CODER_MODEL; using inherited model settings."
            )
            return "inherited"

        presets = model_config.get_presets()
        replacement = {
            "name": PRESET_NAME,
            "chat": {"provider": provider, "name": model},
        }
        if api_base:
            replacement["chat"]["api_base"] = api_base
        presets = [item for item in presets if item.get("name") != PRESET_NAME]
        presets.append(replacement)
        model_config.save_presets(presets)
        plugins.save_plugin_config(
            "_model_config", "", "tiny-coder", {"model_preset": PRESET_NAME}
        )
        if api_key:
            dotenv.save_dotenv_value(f"API_KEY_{provider.upper()}", api_key)
        return "configured"
