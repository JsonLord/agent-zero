import os
from pathlib import Path
from helpers import dotenv, files
from helpers.print_style import PrintStyle

def apply_hf_space_defaults():
    compatible_url = os.environ.get("COMPATIBLE_URL", "").strip()
    compatible_model = os.environ.get("COMPATIBLE_MODEL", "").strip()
    blablador_api_key = os.environ.get("BLABLADOR_API_KEY", "").strip()

    if not compatible_url:
        PrintStyle.warning("COMPATIBLE_URL is not configured")
    if not compatible_model:
        PrintStyle.warning("COMPATIBLE_MODEL is not configured")
    if not blablador_api_key:
        PrintStyle.warning("BLABLADOR_API_KEY is not configured")

    if not (compatible_url or compatible_model or blablador_api_key):
        return

    if blablador_api_key:
        dotenv.save_dotenv_value("API_KEY_OTHER", blablador_api_key)

    try:
        from plugins._model_config.helpers import model_config
        presets = model_config.get_presets()
        if presets and isinstance(presets, list):
            default_preset = presets[0]
            chat_slot = default_preset.setdefault("chat", {})
            if compatible_url or compatible_model or blablador_api_key:
                chat_slot["provider"] = "other"
            if compatible_url:
                chat_slot["api_base"] = compatible_url
            if compatible_model:
                chat_slot["name"] = compatible_model
            if blablador_api_key:
                chat_slot["api_key"] = blablador_api_key
            model_config.save_presets(presets)
    except Exception as e:
        PrintStyle.warning(f"Unable to apply HF Space model defaults: {e}")

if __name__ == "__main__":
    apply_hf_space_defaults()
