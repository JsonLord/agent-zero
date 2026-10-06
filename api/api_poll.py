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
        goal_status = None
        try:
            from plugins._goal.tools import goal

            goal_status = goal.get_goal(context_id)
            if goal_status and goal_status.get("status") == "active" and not running:
                goal_status = goal.reconcile_goal(context_id, running=False)
        except Exception:
            goal_status = None
        semantic_status = status
        if goal_status:
            semantic_status = (
                "working"
                if running and goal_status["status"] == "active"
                else goal_status["status"]
            )
        response = {
            "context_id": context.id,
            "status": semantic_status,
            "running": running,
            "log_progress": context.log.progress,
            "log_from": output.end,
            "result": result if not running else None,
            "goal_id": goal_status.get("goal_id") if goal_status else None,
            "milestone": goal_status.get("current_milestone") if goal_status else "",
            "progress_revision": goal_status.get("progress_revision")
            if goal_status
            else 0,
            "requires_attention": bool(
                goal_status and goal_status.get("requires_attention")
            ),
            "attention_reason": goal_status.get("attention_reason")
            if goal_status
            else "",
            "attention_message": goal_status.get("attention_message")
            if goal_status
            else "",
            "next_poll_after": 2,
        }
        if input.get("include_logs") is True:
            response["logs"] = output.items
        return response
