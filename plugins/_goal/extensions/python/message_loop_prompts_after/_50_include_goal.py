from __future__ import annotations

from agent import LoopData
from helpers.extension import Extension
from plugins._goal.tools import goal


class IncludeGoal(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        try:
            current_goal = goal.get_goal(self.agent.context.id)
        except ValueError:
            current_goal = None

        if not current_goal or current_goal.get("status") != "active":
            loop_data.extras_temporary.pop("current_goal", None)
            return

        remaining = [item["criterion"] for item in current_goal.get("success_criteria", []) if item.get("state") != "PASS"]
        checkpoint = current_goal.get("last_checkpoint") or {}
        loop_data.extras_temporary["current_goal"] = self.agent.read_prompt(
            "agent.extras.goal.md",
            goal_id=current_goal.get("goal_id", ""),
            objective=current_goal.get("objective", ""),
            milestone=current_goal.get("current_milestone", "not set"),
            remaining_criteria="\n".join(f"- {item}" for item in remaining) or "- none defined",
            constraints="\n".join(f"- {item}" for item in current_goal.get("constraints", [])) or "- repository and permission contracts",
            autonomy=(current_goal.get("autonomy") or {}).get("level", "bounded"),
            last_checkpoint=checkpoint.get("note") or checkpoint.get("milestone") or "none",
            requires_attention=str(bool(current_goal.get("requires_attention"))).lower(),
            attention_reason=current_goal.get("attention_reason", ""),
        )
