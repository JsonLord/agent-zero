from python.helpers.api import ApiHandler, Request, Response
from python.helpers import settings, dotenv
import os

class Set(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict:
        # Separate API keys from other settings
        api_keys = {}
        other_settings = {}
        
        for k, v in input.items():
            if k.startswith("api_key_"):
                provider = k.replace("api_key_", "").upper()
                api_keys[provider] = v
            elif k.endswith("_API_KEY") or k.endswith("_API_TOKEN"):
                api_keys[k.upper()] = v
            else:
                other_settings[k] = v
        
        if other_settings:
            settings.set_settings_delta(other_settings)
            
        if api_keys:
            current_settings = settings.get_settings()
            for key, val in api_keys.items():
                # Save to settings
                current_settings["api_keys"][key.lower()] = val
                
                # Save to dotenv and os.environ
                dotenv.save_dotenv_value(f"API_KEY_{key.upper()}", val)
                dotenv.save_dotenv_value(f"{key.upper()}_API_KEY", val)
                
                # Special case for 'other' provider remapping to 'openai'
                if key.upper() == "OTHER":
                    dotenv.save_dotenv_value("OPENAI_API_KEY", val)
                    dotenv.save_dotenv_value("API_KEY_OPENAI", val)
            
            settings.set_settings(current_settings)
            
        return {"status": "success", "message": "Settings updated"}
