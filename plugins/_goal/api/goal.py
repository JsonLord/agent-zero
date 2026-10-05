from __future__ import annotations

from helpers.api import ApiHandler, Request, Response

from plugins._goal.tools import goal


class Goal(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action", "") or "").strip().lower()
        context_id = str(input.get("context_id", "") or "").strip()

        try:
            if action == "get":
                return {"ok": True, "goal": goal.public_goal(goal.get_goal(context_id))}
            if action in {"set", "create"}:
                return self._set(context_id, input)
            if action == "update":
                return self._update(context_id, input)
            if action == "revise":
                current_goal = goal.revise_goal(
                    context_id,
                    objective=input.get("objective"),
                    title=input.get("title"),
                    success_criteria=input.get("success_criteria"),
                    constraints=input.get("constraints"),
                    evidence_required=input.get("evidence_required"),
                    autonomy=input.get("autonomy"),
                )
                return {"ok": True, "goal": goal.public_goal(current_goal)}
            if action == "checkpoint":
                current_goal = goal.checkpoint_goal(
                    context_id,
                    milestone=input.get("milestone"),
                    note=str(input.get("note") or ""),
                    evidence=input.get("evidence"),
                    criterion_updates=input.get("criterion_updates"),
                    requires_attention=input.get("requires_attention"),
                    attention_reason=input.get("attention_reason"),
                    attention_message=input.get("attention_message"),
                )
                return {"ok": True, "goal": goal.public_goal(current_goal)}
            if action == "pause":
                return self._status(context_id, "paused")
            if action == "resume":
                return self._status(context_id, "active")
            if action == "complete":
                current_goal = goal.complete_goal(context_id, note=input.get("note"), result=input.get("result"))
                return {"ok": True, "goal": goal.public_goal(current_goal)}
            if action == "cancel":
                return self._status(context_id, "cancelled")
            if action == "delete":
                goal.delete_goal(context_id)
                return {"ok": True, "goal": None}
        except FileNotFoundError:
            return Response(status=404, response="Goal not found")
        except ValueError as error:
            return Response(status=400, response=str(error))

        return Response(status=400, response=f"Unknown action: {action}")

    def _set(self, context_id: str, input: dict) -> dict:
        current_goal = goal.create_goal(
            context_id,
            str(input.get("objective") or ""),
            created_by=str(input.get("created_by") or "user"),
            token_budget=input.get("token_budget"),
            title=str(input.get("title") or ""),
            owner_profile=str(input.get("owner_profile") or ""),
            success_criteria=input.get("success_criteria"),
            constraints=input.get("constraints"),
            evidence_required=input.get("evidence_required"),
            autonomy=input.get("autonomy"),
            idempotency_key=str(input.get("idempotency_key") or ""),
        )
        return {"ok": True, "goal": goal.public_goal(current_goal)}

    def _update(self, context_id: str, input: dict) -> dict:
        current = goal.get_goal(context_id)
        updated_goal = goal.update_goal(
            context_id,
            objective=input.get("objective") if "objective" in input else None,
            status=input.get("status") if "status" in input else None,
            note=input.get("note") if "note" in input else None,
            token_budget=input.get("token_budget") if "token_budget" in input else None,
        )
        return {
            "ok": True,
            "goal": goal.public_goal(updated_goal),
            "reactivated": (
                current is not None
                and current.get("status") in goal.FINAL_STATUSES | {"blocked"}
                and updated_goal.get("status") == "active"
            ),
        }

    def _status(self, context_id: str, status: str) -> dict:
        current_goal = goal.update_goal(context_id, status=status)
        return {"ok": True, "goal": goal.public_goal(current_goal)}
