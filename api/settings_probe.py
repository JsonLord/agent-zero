import os

from helpers import settings
from helpers.api import ApiHandler, Request, Response


class SettingsProbe(ApiHandler):
    """API-key protected inspection and reversible safe-setting mutation."""

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action") or "get").strip().lower()
        if action == "get":
            output = settings.convert_out(settings.get_settings())
            from plugins._model_config.helpers import model_config

            configured = model_config.get_config().get("chat_model", {})
            return {
                "ok": True,
                **output,
                "runtime": {
                    "uid": os.geteuid() if hasattr(os, "geteuid") else None,
                    "gid": os.getegid() if hasattr(os, "getegid") else None,
                },
                "main_model": {
                    key: configured.get(key, "")
                    for key in ("provider", "name", "api_base")
                },
            }
        if action == "set_time_format":
            value = str(input.get("value") or "").strip().lower()
            if value not in {settings.TIME_FORMAT_12H, settings.TIME_FORMAT_24H}:
                return Response("Invalid time format", status=400)
            current = settings.set_settings_delta({"time_format": value})
            return {"ok": True, "time_format": current["time_format"]}
        return Response("Unknown action", status=400)
