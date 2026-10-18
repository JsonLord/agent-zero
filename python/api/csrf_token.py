from python.helpers.api import (
    ApiHandler,
    Input,
    Output,
    Request,
    Response,
    session,
)
from python.helpers import runtime, csrf

class GetCsrfToken(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:
        token = csrf.generate_csrf_token()
        return {"token": token, "runtime_id": runtime.get_runtime_id()}
