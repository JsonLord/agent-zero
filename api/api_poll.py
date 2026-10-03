from __future__ import annotations

from agent import AgentContext
from helpers.api import ApiHandler, Request, Response


class ApiPoll(ApiHandler):
    """API-key protected status for chats started through ``api_message``."""

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
        context_id = str(input.get("context_id", "") or "").strip()
        if not context_id:
            return Response("Missing context_id", status=400)
        context = AgentContext.get(context_id)
        if context is None:
            return Response("Context not found", status=404)

        output = context.log.output(start=max(0, int(input.get("log_from", 0) or 0)))
        result = None
        for item in reversed(output.items):
            if item.get("type") in {"agent", "assistant", "response"}:
                result = item.get("content")
                break
        running = context.is_running()
        status = "running" if running else "completed"
        if not running and context.task and context.task.is_ready():
            try:
                result = context.task.result_sync(timeout=0)
            except Exception:
                status = "failed"
        return {
            "context_id": context.id,
            "status": status,
            "running": running,
            "log_progress": context.log.progress,
            "log_from": output.end,
            "logs": output.items,
            "result": result if not running else None,
        }
