from python.helpers.api import ApiHandler, Request, Output
import os

class Docs(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict:
        auth_token = os.getenv("AUTHENTICATION_TOKEN")
        auth_type = "Bearer token required" if auth_token else "Basic Auth or API Key required"
        
        return {
            "title": "Agent-skillset API Documentation",
            "authentication": auth_type,
            "endpoints": [
                {
                    "path": "/health",
                    "method": "GET",
                    "description": "Check if the service is running.",
                    "auth_required": False
                },
                {
                    "path": "/chat",
                    "method": "POST",
                    "description": "Send a message and receive the final response.",
                    "parameters": {
                        "message": "The text message to send (required).",
                        "subagent": "The name of the agent profile to use (optional).",
                        "file": "Base64 encoded file content for context (optional).",
                        "file_name": "The name of the file being uploaded (optional).",
                        "context": "The ID of an existing chat context (optional)."
                    },
                    "headers": {
                        "Authorization": "Bearer YOUR_AUTHENTICATION_TOKEN"
                    }
                },
                {
                    "path": "/stream",
                    "method": "POST",
                    "description": "Stream the agent's response using Server-Sent Events (SSE).",
                    "parameters": {
                        "message": "The text message to send (required).",
                        "subagent": "The name of the agent profile to use (optional).",
                        "file": "Base64 encoded file content for context (optional).",
                        "file_name": "The name of the file being uploaded (optional).",
                        "context": "The ID of an existing chat context (optional)."
                    },
                    "headers": {
                        "Authorization": "Bearer YOUR_AUTHENTICATION_TOKEN"
                    }
                },
                {
                    "path": "/set",
                    "method": "POST",
                    "description": "Dynamically update application settings and API keys.",
                    "parameters": {
                        "any_setting_key": "The value to set for that setting.",
                        "api_key_PROVIDER": "Set the API key for a specific provider (e.g., api_key_openai)."
                    },
                    "headers": {
                        "Authorization": "Bearer YOUR_AUTHENTICATION_TOKEN"
                    }
                },
                {
                    "path": "/get",
                    "method": "GET",
                    "description": "Retrieve the current application settings.",
                    "headers": {
                        "Authorization": "Bearer YOUR_AUTHENTICATION_TOKEN"
                    }
                }
            ]
        }
