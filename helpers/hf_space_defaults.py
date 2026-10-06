import os
from helpers import dotenv
from helpers.print_style import PrintStyle


def apply_hf_space_defaults() -> dict[str, bool]:
    """Apply only non-empty Space defaults and return a secret-free summary."""
    compatible_url = os.environ.get("COMPATIBLE_URL", "").strip()
    compatible_model = os.environ.get("COMPATIBLE_MODEL", "").strip()
    blablador_api_key = os.environ.get("BLABLADOR_API_KEY", "").strip()

    if not compatible_url: PrintStyle.warning("COMPATIBLE_URL is not configured")
    if not compatible_model: PrintStyle.warning("COMPATIBLE_MODEL is not configured")
    if not blablador_api_key: PrintStyle.warning("BLABLADOR_API_KEY is not configured")
    if not (compatible_url or compatible_model or blablador_api_key):
        return {"url": False, "model": False, "api_key": False}

    if blablador_api_key:
        dotenv.save_dotenv_value("API_KEY_OTHER", blablador_api_key)

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
    model_config.save_presets(presets)
    return {"url": bool(compatible_url), "model": bool(compatible_model), "api_key": bool(blablador_api_key)}


if __name__ == "__main__":
    apply_hf_space_defaults()
