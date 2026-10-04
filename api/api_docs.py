from helpers.api import ApiHandler, Request, Response
import json

API_DOCS_PAYLOAD = {
    "title": "Open Operator API Documentation",
    "description": "API documentation for Open Operator (Agent Zero)",
    "endpoints": [
        {
            "path": "/health",
            "method": "GET",
            "purpose": "Health check endpoint for Hugging Face Spaces status probe",
            "request": {},
            "response": {"status": "ok"}
        },
        {
            "path": "/api-docs",
            "method": "GET",
            "purpose": "API documentation endpoint listing all endpoints",
            "request": {},
            "response": {"title": "Open Operator API Documentation", "endpoints": "..."}
        },
        {
            "path": "/api/health",
            "method": "GET",
            "purpose": "System health and git status details",
            "request": {},
            "response": {"gitinfo": {"version": "v1.6", "commit_time": "2026-01-01 00:00:00"}, "error": None}
        },
        {
            "path": "/api/message",
            "method": "POST",
            "purpose": "Send a synchronous message to the agent context",
            "request": {"message": "Hello agent", "context_id": "default"},
            "response": {"response": "Agent reply text"}
        },
        {
            "path": "/api/message_async",
            "method": "POST",
            "purpose": "Send an asynchronous message to the agent context",
            "request": {"message": "Hello agent", "context_id": "default"},
            "response": {"status": "queued"}
        },
        {
            "path": "/api/settings_get",
            "method": "GET",
            "purpose": "Retrieve runtime and user settings",
            "request": {},
            "response": {"settings": {"chat_model": "gpt-4o"}}
        },
        {
            "path": "/api/settings_set",
            "method": "POST",
            "purpose": "Update runtime and user settings",
            "request": {"settings": {"timezone": "UTC"}},
            "response": {"success": True}
        },
        {
            "path": "/api/chat_create",
            "method": "POST",
            "purpose": "Create a new chat context session",
            "request": {"name": "New Chat"},
            "response": {"context_id": "abc-123"}
        },
        {
            "path": "/api/chat_remove",
            "method": "POST",
            "purpose": "Remove a chat context session",
            "request": {"context_id": "abc-123"},
            "response": {"success": True}
        },
        {
            "path": "/api/chat_load",
            "method": "POST",
            "purpose": "Load history for a specific chat context",
            "request": {"context_id": "abc-123"},
            "response": {"history": []}
        },
        {
            "path": "/api/chat_reset",
            "method": "POST",
            "purpose": "Reset messages in a chat context",
            "request": {"context_id": "abc-123"},
            "response": {"success": True}
        },
        {
            "path": "/api/history_get",
            "method": "GET",
            "purpose": "Retrieve history for active context",
            "request": {},
            "response": {"history": []}
        },
        {
            "path": "/api/upload",
            "method": "POST",
            "purpose": "Upload file to context work directory",
            "request": {"file": "binary data"},
            "response": {"filename": "example.txt", "path": "/a0/usr/workdir/example.txt"}
        }
    ]
}

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
        return Response(
            response=json.dumps(API_DOCS_PAYLOAD, indent=2),
            status=200,
            mimetype="application/json"
        )
