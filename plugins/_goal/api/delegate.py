from __future__ import annotations

import uuid

from agent import AgentContext, AgentContextType, UserMessage
from helpers import subagents
from helpers.api import ApiHandler, Request, Response
from initialize import initialize_agent
from plugins._goal.tools import goal


class Delegate(ApiHandler):
    """API-key protected structured goal delegation for Spynel."""

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
        action = str(input.get("action") or "create").strip().lower()
        if action != "create":
            return self._operate(action, input)
        profile = str(input.get("agent_profile") or "").strip()
        objective = str(input.get("objective") or input.get("message") or "").strip()
        idempotency_key = str(input.get("idempotency_key") or "").strip()
        idempotency_scope = str(input.get("idempotency_scope") or "").strip()
        project_name = input.get("project_name")
        if not profile or profile not in subagents.get_available_agents_dict(
            project_name
        ):
            return Response(
                '{"error":"Agent profile not found"}',
                status=404,
                mimetype="application/json",
            )
        if not objective:
            return Response(
                '{"error":"Goal objective is required"}',
                status=400,
                mimetype="application/json",
            )

        if idempotency_key:
            existing = goal._find_idempotent(idempotency_key, idempotency_scope)
            if existing:
                return {
                    "ok": True,
                    "accepted": False,
                    "idempotent_replay": True,
                    "context_id": existing["context_id"],
                    "goal_id": existing["goal_id"],
                    "goal": goal.public_goal(existing),
                }

        context = AgentContext(
            config=initialize_agent(override_settings={"agent_profile": profile}),
            type=AgentContextType.USER,
        )
        default_level = (
            "bounded"
            if profile in {"reviewer", "security", "docs"}
            else "operational"
            if profile == "shipper"
            else "implementation"
        )
        current_goal = goal.create_goal(
            context.id,
            objective,
            created_by="spynel",
            owner_profile=profile,
            title=str(input.get("title") or ""),
            parent_goal_id=input.get("parent_goal_id"),
            success_criteria=input.get("success_criteria"),
            constraints=input.get("constraints"),
            evidence_required=input.get("evidence_required"),
            autonomy=input.get("autonomy") or {"level": default_level},
            depends_on=input.get("depends_on"),
            idempotency_key=idempotency_key,
            idempotency_scope=idempotency_scope,
        )
        should_start = goal.dependencies_ready(current_goal)
        if not should_start:
            current_goal = goal.update_goal(context.id, status="pending")
        else:
            message_id = str(uuid.uuid4())
            context.log.log(
                type="user", heading="", content=objective, kvps={}, id=message_id
            )
            context.communicate(
                UserMessage(message=objective, attachments=[], id=message_id)
            )
        return {
            "ok": True,
            "accepted": True,
            "context_id": context.id,
            "goal_id": current_goal["goal_id"],
            "state": current_goal["status"],
            "goal": goal.public_goal(current_goal),
        }

    def _operate(self, action: str, input: dict) -> dict | Response:
        context_id = str(input.get("context_id") or "").strip()
        current = goal.get_goal(context_id) if context_id else None
        if not current or (
            input.get("goal_id") and input.get("goal_id") != current["goal_id"]
        ):
            return Response(
                '{"error":"Goal not found"}', status=404, mimetype="application/json"
            )
        if action in {"get", "status"}:
            updated = current
        elif action == "checkpoint":
            updated = goal.checkpoint_goal(
                context_id,
                milestone=input.get("milestone"),
                note=str(input.get("note") or ""),
                evidence=input.get("evidence"),
                criterion_updates=input.get("criterion_updates"),
                requires_attention=input.get("requires_attention"),
                attention_reason=input.get("attention_reason"),
                attention_message=input.get("attention_message"),
            )
        elif action == "revise":
            updated = goal.revise_goal(
                context_id,
                objective=input.get("objective"),
                title=input.get("title"),
                success_criteria=input.get("success_criteria"),
                constraints=input.get("constraints"),
                evidence_required=input.get("evidence_required"),
                autonomy=input.get("autonomy"),
            )
        elif action in {"pause", "resume", "cancel"}:
            updated = (
                goal.resume_goal(context_id)
                if action == "resume"
                else goal.update_goal(
                    context_id,
                    status={"pause": "paused", "cancel": "cancelled"}[action],
                )
            )
            context = AgentContext.get(context_id)
            if context is not None and action != "resume":
                context.paused = action != "resume"
        elif action == "complete":
            updated = goal.complete_goal(
                context_id, note=input.get("note"), result=input.get("result")
            )
        elif action == "children":
            return {
                "ok": True,
                "goal_id": current["goal_id"],
                "children": [
                    goal.public_goal(item)
                    for item in goal.list_child_goals(current["goal_id"])
                ],
            }
        else:
            return Response(
                '{"error":"Unknown goal action"}',
                status=400,
                mimetype="application/json",
            )
        return {
            "ok": True,
            "context_id": updated["context_id"],
            "goal_id": updated["goal_id"],
            "goal": goal.public_goal(updated),
        }
