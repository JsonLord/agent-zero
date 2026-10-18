from python.helpers.api import ApiHandler, Request, Response
from python.helpers import settings

class Get(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict:
        current_settings = settings.get_settings()
        return {"settings": current_settings}
