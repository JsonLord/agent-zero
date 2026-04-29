from helpers.api import ApiHandler, Input, Output, Request

class Health(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:
        return {"status": "ok", "message": "Space is running"}
