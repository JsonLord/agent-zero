from helpers.api import ApiHandler, Request, Response

class ApiDocs(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        return {
            "title": "Agent Zero API Docs",
            "endpoints": [
                {
                    "path": "/api/message",
                    "method": "POST",
                    "purpose": "Send a message to the agent",
                    "request_example": {"text": "hello", "context": "optional_context_id"},
                    "response_example": {"message": "...", "context": "..."}
                },
                {
                    "path": "/api/health",
                    "method": "GET",
                    "purpose": "Health check for the application",
                    "response_example": {"gitinfo": {}, "error": None}
                }
            ]
        }
