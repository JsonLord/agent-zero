from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
import uuid
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from helpers import files
from helpers.tool import Response, Tool

PLUGIN_NAME = "_goal"
GOALS_DIR = "goals"
ACTIVE_STATUSES = {"active", "interrupted", "paused", "blocked", "pending"}
FINAL_STATUSES = {"completed", "partially_verified", "failed", "cancelled"}
VALID_STATUSES = ACTIVE_STATUSES | FINAL_STATUSES
LEGACY_STATUS = {"complete": "completed"}
ATTENTION_REASONS = {
    "approval_required",
    "ambiguous_requirement",
    "scope_expansion",
    "external_credential_needed",
    "repeated_failure",
    "security_boundary",
    "conflicting_evidence",
    "manual_action_required",
}
AUTONOMY_LEVELS = {"bounded", "implementation", "operational"}
MAX_GOAL_DEPTH = max(1, int(os.getenv("A0_GOAL_MAX_DEPTH", "3")))
MAX_CHILD_GOALS = max(1, int(os.getenv("A0_GOAL_MAX_CHILDREN", "8")))
MAX_CONCURRENT_GOALS = max(1, int(os.getenv("A0_GOAL_MAX_CONCURRENT", "4")))
MAX_HISTORY = 25
CRITERION_STATES = {"PASS", "FAIL", "NOT_VERIFIED"}
_MUTATION_LOCK = threading.RLock()
STATE_TRANSITIONS = {
    "pending": {"active", "blocked", "interrupted", "cancelled"},
    "active": {
        "paused",
        "blocked",
        "interrupted",
        "completed",
        "partially_verified",
        "failed",
        "cancelled",
    },
    "paused": {"active", "blocked", "interrupted", "cancelled"},
    "interrupted": {"active", "blocked", "cancelled"},
    "blocked": {"active", "cancelled"},
    "completed": set(),
    "partially_verified": set(),
    "failed": set(),
    "cancelled": set(),
}


def _locked(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _MUTATION_LOCK:
            return function(*args, **kwargs)

    return wrapped


class GoalTool(Tool):
    async def execute(
        self,
        action: str = "",
        objective: str = "",
        status: str = "",
        note: str = "",
        token_budget: int | None = None,
        **kwargs,
    ) -> Response:
        action = str(action or self.args.get("action") or "get").strip().lower()
        context_id = self.agent.context.id
        try:
            if action in {"get", "show", "status"}:
                return Response(
                    message=summarize_goal(get_goal(context_id)), break_loop=False
                )
            if action in {"create", "set"}:
                current = create_goal(
                    context_id,
                    objective,
                    created_by="model",
                    token_budget=token_budget,
                    **_goal_kwargs(kwargs),
                )
                return Response(
                    message=f"Goal created: {current['objective']}", break_loop=False
                )
            if action == "checkpoint":
                current = checkpoint_goal(
                    context_id,
                    milestone=kwargs.get("milestone"),
                    note=note,
                    evidence=kwargs.get("evidence"),
                    requires_attention=kwargs.get("requires_attention"),
                    attention_reason=kwargs.get("attention_reason"),
                    attention_message=kwargs.get("attention_message"),
                    criterion_updates=kwargs.get("criterion_updates"),
                )
                return Response(message=summarize_goal(current), break_loop=False)
            if action == "revise":
                current = revise_goal(
                    context_id,
                    objective=objective or None,
                    success_criteria=kwargs.get("success_criteria"),
                    constraints=kwargs.get("constraints"),
                    evidence_required=kwargs.get("evidence_required"),
                )
                return Response(message=summarize_goal(current), break_loop=False)
            if action in {"complete", "blocked"}:
                status = action
            if action in {"update", "complete", "blocked"}:
                if status in {"complete", "completed"}:
                    current = complete_goal(context_id, note=note or None)
                elif status == "blocked":
                    current = update_goal(
                        context_id,
                        status="blocked",
                        note=note or None,
                        requires_attention=True,
                        attention_reason=kwargs.get("attention_reason")
                        or "repeated_failure",
                    )
                else:
                    return Response(
                        message="Model goal updates require checkpoint, revise, complete, or blocked.",
                        break_loop=False,
                    )
                return Response(message=summarize_goal(current), break_loop=False)
        except (FileNotFoundError, ValueError) as error:
            return Response(message=str(error), break_loop=False)
        return Response(message="Unknown goal action.", break_loop=False)


def _goal_kwargs(values: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "title",
        "owner_profile",
        "parent_goal_id",
        "success_criteria",
        "constraints",
        "evidence_required",
        "autonomy",
        "idempotency_key",
        "idempotency_scope",
        "depends_on",
    }
    return {key: values[key] for key in allowed if key in values}


def get_goal(context_id: str) -> dict[str, Any] | None:
    context_id = _require_context_id(context_id)
    path = Path(_goal_path(context_id))
    legacy = Path(_legacy_goal_path(context_id))
    source = path if path.is_file() else legacy
    if not source.is_file():
        return None
    try:
        raw = json.loads(files.read_file(str(source)))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    normalized = _normalize_goal(raw, context_id=context_id)
    if source == legacy and path != legacy:
        _write_goal(normalized)
        legacy.unlink(missing_ok=True)
    return normalized if normalized.get("objective") else None


def get_goal_by_id(goal_id: str) -> dict[str, Any] | None:
    for path in _goals_directory().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("goal_id") == goal_id:
            return _normalize_goal(raw, context_id=str(raw.get("context_id") or ""))
    return None


@_locked
def create_goal(
    context_id: str,
    objective: str,
    *,
    created_by: str = "user",
    token_budget: int | None = None,
    title: str = "",
    owner_profile: str = "",
    parent_goal_id: str | None = None,
    success_criteria: Any = None,
    constraints: Any = None,
    evidence_required: Any = None,
    autonomy: Any = None,
    idempotency_key: str = "",
    idempotency_scope: str = "",
    depends_on: Any = None,
    goal_id: str | None = None,
) -> dict[str, Any]:
    context_id = _require_context_id(context_id)
    objective = _required_objective(objective)
    idempotency_scope = _clean_text(idempotency_scope) or (
        f"parent:{parent_goal_id}" if parent_goal_id else f"context:{context_id}"
    )
    if idempotency_key:
        existing = _find_idempotent(idempotency_key, idempotency_scope)
        if existing:
            return existing
    parent = get_goal_by_id(parent_goal_id) if parent_goal_id else None
    if parent_goal_id and not parent:
        raise ValueError("Parent goal not found")
    if parent and int(parent.get("depth", 0)) >= MAX_GOAL_DEPTH:
        raise ValueError("Maximum goal depth exceeded")
    if parent and len(list_child_goals(parent_goal_id)) >= MAX_CHILD_GOALS:
        raise ValueError("Maximum child goals exceeded")
    if parent and not _string_list(depends_on):
        active_workers = sum(
            bool(item.get("status") == "active" and item.get("parent_goal_id"))
            for item in _all_goals()
        )
        if active_workers >= MAX_CONCURRENT_GOALS:
            raise ValueError("Maximum concurrent worker goals exceeded")
    new_goal_id = _clean_text(goal_id) or f"goal_{uuid.uuid4().hex}"
    dependency_ids = _string_list(depends_on)
    _validate_dependencies(new_goal_id, parent_goal_id, dependency_ids)
    now = _now()
    previous = get_goal(context_id)
    goal = {
        "goal_id": new_goal_id,
        "context_id": context_id,
        "owner_profile": _clean_text(owner_profile),
        "parent_goal_id": parent_goal_id,
        "title": _clean_text(title) or objective[:120],
        "objective": objective,
        "success_criteria": _normalize_criteria(success_criteria),
        "constraints": _string_list(constraints),
        "evidence_required": _string_list(evidence_required),
        "autonomy": _normalize_autonomy(autonomy),
        "status": "pending"
        if dependency_ids
        and not all(
            get_goal_by_id(item).get("status") == "completed" for item in dependency_ids
        )
        else "active",
        "current_milestone": "",
        "goal_revision": 1,
        "progress_revision": 1,
        "requires_attention": False,
        "attention_reason": "",
        "attention_message": "",
        "last_checkpoint": {},
        "result": {},
        "children": [],
        "depends_on": dependency_ids,
        "depth": int(parent.get("depth", 0)) + 1 if parent else 0,
        "idempotency_key": _clean_text(idempotency_key),
        "idempotency_scope": idempotency_scope,
        "history": [],
        "created_by": _clean_created_by(created_by),
        "token_budget": _clean_token_budget(token_budget),
        "created_at": now,
        "active_since": now,
        "elapsed_seconds": 0,
        "updated_at": now,
        "note": "",
    }
    if previous:
        goal["history"] = [
            {
                "revision": previous.get("goal_revision", 1),
                "at": previous.get("updated_at"),
                "definition": _definition(previous),
            }
        ]
    _write_goal(goal)
    if parent:
        parent["children"] = list(
            dict.fromkeys([*parent.get("children", []), goal["goal_id"]])
        )
        _semantic_change(parent, history=False)
        _write_goal(parent)
    return goal


@_locked
def revise_goal(
    context_id: str,
    *,
    objective: str | None = None,
    title: str | None = None,
    success_criteria: Any = None,
    constraints: Any = None,
    evidence_required: Any = None,
    autonomy: Any = None,
) -> dict[str, Any]:
    goal = _required_goal(context_id)
    goal["history"] = [
        *goal.get("history", []),
        {
            "revision": goal["goal_revision"],
            "at": goal["updated_at"],
            "definition": _definition(goal),
        },
    ][-MAX_HISTORY:]
    if objective is not None:
        goal["objective"] = _required_objective(objective)
    if title is not None:
        goal["title"] = _clean_text(title) or goal["title"]
    if success_criteria is not None:
        goal["success_criteria"] = _normalize_criteria(success_criteria)
    if constraints is not None:
        goal["constraints"] = _string_list(constraints)
    if evidence_required is not None:
        goal["evidence_required"] = _string_list(evidence_required)
    if autonomy is not None:
        goal["autonomy"] = _normalize_autonomy(autonomy)
    goal["goal_revision"] += 1
    _semantic_change(goal, history=False)
    _write_goal(goal)
    return goal


@_locked
def checkpoint_goal(
    context_id: str,
    *,
    milestone: Any = None,
    note: str = "",
    evidence: Any = None,
    requires_attention: Any = None,
    attention_reason: Any = None,
    attention_message: Any = None,
    criterion_updates: Any = None,
) -> dict[str, Any]:
    goal = _required_goal(context_id)
    if (
        milestone is None
        and not note
        and evidence is None
        and requires_attention is None
        and not criterion_updates
    ):
        return goal
    checkpoint = {
        "milestone": _clean_text(milestone),
        "note": _clean_text(note),
        "evidence": _string_list(evidence),
    }
    previous = goal.get("last_checkpoint") or {}
    changed = checkpoint != {key: previous.get(key) for key in checkpoint}
    if milestone is not None and checkpoint["milestone"] != goal.get(
        "current_milestone"
    ):
        goal["current_milestone"] = checkpoint["milestone"]
        changed = True
    if criterion_updates:
        changed = _apply_criterion_updates(goal, criterion_updates) or changed
    if requires_attention is not None:
        requested = bool(requires_attention)
        reason = _clean_text(attention_reason) if requested else ""
        if reason and reason not in ATTENTION_REASONS:
            raise ValueError("Invalid attention reason")
        state = (requested, reason, _clean_text(attention_message) if requested else "")
        if state != (
            goal.get("requires_attention"),
            goal.get("attention_reason"),
            goal.get("attention_message"),
        ):
            (
                goal["requires_attention"],
                goal["attention_reason"],
                goal["attention_message"],
            ) = state
            changed = True
    if changed:
        goal["last_checkpoint"] = {**checkpoint, "at": _now()}
        goal["note"] = checkpoint["note"] or goal.get("note", "")
        _semantic_change(goal, history=False)
        _write_goal(goal)
    return goal


@_locked
def update_goal(
    context_id: str,
    *,
    objective: str | None = None,
    status: str | None = None,
    note: str | None = None,
    token_budget: int | None = None,
    requires_attention: bool | None = None,
    attention_reason: str | None = None,
    attention_message: str | None = None,
) -> dict[str, Any]:
    goal = _required_goal(context_id)
    changed = False
    if objective is not None and _required_objective(objective) != goal["objective"]:
        revise_goal(context_id, objective=objective)
        goal = _required_goal(context_id)
    if status is not None:
        normalized = _normalize_status(status)
        if normalized != goal["status"]:
            if normalized == "active":
                raise ValueError("Use resume_goal() to activate a goal")
            if normalized in {"completed", "partially_verified", "failed"}:
                raise ValueError("Use complete_goal() for evidence-based completion")
            if normalized not in STATE_TRANSITIONS.get(goal["status"], set()):
                raise ValueError(
                    f"Invalid goal transition: {goal['status']} -> {normalized}"
                )
            _apply_status(goal, normalized)
            changed = True
    if note is not None and _clean_text(note) != goal.get("note"):
        goal["note"] = _clean_text(note)
        changed = True
    if token_budget is not None:
        goal["token_budget"] = _clean_token_budget(token_budget)
        changed = True
    if requires_attention is not None:
        reason = _clean_text(attention_reason) if requires_attention else ""
        if reason and reason not in ATTENTION_REASONS:
            raise ValueError("Invalid attention reason")
        goal["requires_attention"] = requires_attention
        goal["attention_reason"] = reason
        goal["attention_message"] = (
            _clean_text(attention_message) if requires_attention else ""
        )
        changed = True
    if changed:
        _semantic_change(goal, history=False)
        _write_goal(goal)
    return goal


@_locked
def complete_goal(
    context_id: str, *, note: str | None = None, result: Any = None
) -> dict[str, Any]:
    goal = _required_goal(context_id)
    unfinished = [
        child
        for child in list_child_goals(goal["goal_id"])
        if child.get("status") not in FINAL_STATUSES
    ]
    states = [item["state"] for item in goal.get("success_criteria", [])]
    status = (
        "partially_verified"
        if unfinished or not states
        else "completed"
        if all(state == "PASS" for state in states)
        else "failed"
        if "FAIL" in states
        else "partially_verified"
    )
    _apply_status(goal, status)
    goal["note"] = _clean_text(note) if note is not None else goal.get("note", "")
    goal["result"] = result if isinstance(result, dict) else {}
    goal["requires_attention"] = status != "completed"
    goal["attention_reason"] = (
        "conflicting_evidence"
        if status == "failed"
        else "manual_action_required"
        if status == "partially_verified"
        else ""
    )
    goal["attention_message"] = (
        "Complete or cancel active child goals first."
        if unfinished
        else "Completion requires verified success criteria."
        if not states
        else "Review unmet success criteria."
        if status != "completed"
        else ""
    )
    _semantic_change(goal, history=False)
    _write_goal(goal)
    if status == "completed":
        _activate_ready_dependents(goal["goal_id"])
    return goal


def list_child_goals(parent_goal_id: str) -> list[dict[str, Any]]:
    result = []
    for path in _goals_directory().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("parent_goal_id") == parent_goal_id:
            result.append(
                _normalize_goal(raw, context_id=str(raw.get("context_id") or ""))
            )
    return result


def create_subgoal_context(
    parent_context_id: str, profile: str, objective: str, *, depends_on: Any = None
) -> dict[str, Any]:
    """Create a validated fresh worker context for an interactive child goal."""
    from agent import AgentContext, AgentContextType, UserMessage
    from helpers import subagents
    from initialize import initialize_agent

    parent = _required_goal(parent_context_id)
    profile = _clean_text(profile).lstrip("@").lower()
    if profile not in subagents.get_available_agents_dict(None):
        raise ValueError("Agent profile not found")
    context = AgentContext(
        config=initialize_agent(override_settings={"agent_profile": profile}),
        type=AgentContextType.USER,
    )
    level = (
        "bounded"
        if profile in {"reviewer", "security", "docs"}
        else "operational"
        if profile == "shipper"
        else "implementation"
    )
    child = create_goal(
        context.id,
        objective,
        created_by="user",
        owner_profile=profile,
        parent_goal_id=parent["goal_id"],
        depends_on=depends_on,
        autonomy={"level": level},
    )
    if dependencies_ready(child):
        context.communicate(UserMessage(message=child["objective"], attachments=[]))
    else:
        child = update_goal(context.id, status="pending")
    return child


def dependencies_ready(goal: dict[str, Any]) -> bool:
    dependencies = [get_goal_by_id(item) for item in goal.get("depends_on", [])]
    return all(item and item.get("status") == "completed" for item in dependencies)


def _validate_dependencies(
    goal_id: str,
    parent_goal_id: str | None,
    dependency_ids: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> None:
    dependency_ids = (
        dependency_ids if dependency_ids is not None else (depends_on or [])
    )
    if not dependency_ids:
        return
    if not parent_goal_id:
        raise ValueError("Dependencies are only supported between sibling child goals")
    for dependency_id in dependency_ids:
        if dependency_id == goal_id:
            raise ValueError("A goal cannot depend on itself")
        dependency = get_goal_by_id(dependency_id)
        if dependency is None:
            raise ValueError(f"Dependency not found: {dependency_id}")
        if dependency.get("parent_goal_id") != parent_goal_id:
            raise ValueError("Dependencies must be sibling goals under the same parent")
        if _dependency_reaches(dependency, goal_id, set()):
            raise ValueError("Goal dependency cycle detected")


def _dependency_reaches(goal: dict[str, Any], target: str, seen: set[str]) -> bool:
    identity = str(goal.get("goal_id") or "")
    if identity in seen:
        return False
    seen.add(identity)
    for dependency_id in goal.get("depends_on", []):
        if dependency_id == target:
            return True
        dependency = get_goal_by_id(dependency_id)
        if dependency and _dependency_reaches(dependency, target, seen):
            return True
    return False


def resume_goal(context_id: str) -> dict[str, Any]:
    """Resume at most once after dependency validation; never reopen final work."""
    with _MUTATION_LOCK:
        current = _required_goal(context_id)
        if current["status"] in FINAL_STATUSES:
            raise ValueError(
                f"Cannot resume a {current['status']} goal; revise or create a new goal"
            )
        if not dependencies_ready(current):
            if current["status"] != "pending":
                _apply_status(current, "pending")
                _semantic_change(current, history=False)
                _write_goal(current)
            return current
        try:
            from agent import AgentContext, UserMessage

            context = AgentContext.get(context_id)
            if context is None:
                return recover_goal_context(current["goal_id"])
            if context.is_running():
                if current["status"] != "active":
                    _apply_status(current, "active")
                    _semantic_change(current, history=False)
                    _write_goal(current)
                return current
            context.paused = False
            context.communicate(
                UserMessage(message=current["objective"], attachments=[])
            )
            if not context.is_running():
                return _mark_interrupted(
                    current, "Worker did not enter a running state."
                )
            _apply_status(current, "active")
            current["requires_attention"] = False
            current["attention_reason"] = current["attention_message"] = ""
            _semantic_change(current, history=False)
            _write_goal(current)
            return current
        except Exception as error:
            return _mark_interrupted(
                current, f"Worker resume failed: {type(error).__name__}"
            )


def recover_goal_context(goal_id: str) -> dict[str, Any]:
    """Explicitly continue an interrupted goal in a fresh native context.

    Recovery preserves the durable goal identity and evidence. Operational
    goals stop at an approval boundary because replaying external work after a
    process restart is never safe by inference.
    """
    with _MUTATION_LOCK:
        current = get_goal_by_id(goal_id)
        if current is None:
            raise FileNotFoundError("Goal not found")
        if current["status"] in FINAL_STATUSES:
            raise ValueError(f"Cannot recover a {current['status']} goal")
        if not dependencies_ready(current):
            if current["status"] != "pending":
                _apply_status(current, "pending")
                _semantic_change(current, history=False)
                _write_goal(current)
            return current
        if current.get("autonomy", {}).get("level") == "operational":
            current["requires_attention"] = True
            current["attention_reason"] = "approval_required"
            current["attention_message"] = (
                "Operational goal recovery requires explicit approval before replay."
            )
            if current["status"] == "active":
                _apply_status(current, "interrupted")
            _semantic_change(current, history=False)
            _write_goal(current)
            return current

        from agent import AgentContext, AgentContextType, UserMessage
        from initialize import initialize_agent

        profile = _clean_text(current.get("owner_profile")) or "agent0"
        context = AgentContext(
            config=initialize_agent(override_settings={"agent_profile": profile}),
            type=AgentContextType.USER,
        )
        old_context_id = current["context_id"]
        current["context_id"] = context.id
        current["history"] = [
            *current.get("history", []),
            {
                "revision": current.get("goal_revision", 1),
                "at": _now(),
                "event": "context_recovered",
                "previous_context_id": old_context_id,
            },
        ][-MAX_HISTORY:]
        _apply_status(current, "active")
        current["requires_attention"] = False
        current["attention_reason"] = ""
        current["attention_message"] = ""
        _semantic_change(current, history=False)
        _write_goal(current)
        Path(_goal_path(old_context_id)).unlink(missing_ok=True)
        context.communicate(UserMessage(message=current["objective"], attachments=[]))
        if not context.is_running():
            return _mark_interrupted(current, "Recovered worker did not start.")
        return current


def reconcile_goal(
    context_id: str, *, running: bool | None = None
) -> dict[str, Any] | None:
    """Convert durable-but-stale active state to explicitly resumable state."""
    with _MUTATION_LOCK:
        current = get_goal(context_id)
        if not current or current["status"] != "active":
            return current
        if running is None:
            try:
                from agent import AgentContext

                context = AgentContext.get(context_id)
                running = bool(context and context.is_running())
            except Exception:
                running = False
        return (
            current
            if running
            else _mark_interrupted(
                current, "Worker execution stopped; explicit resume is required."
            )
        )


def reconcile_persisted_goals(context_resolver=None) -> list[dict[str, Any]]:
    reconciled = []
    for item in _all_goals():
        if item.get("status") != "active":
            continue
        running = None
        if context_resolver is not None:
            context = context_resolver(item["context_id"])
            running = bool(context and context.is_running())
        reconciled.append(reconcile_goal(item["context_id"], running=running) or item)
    return reconciled


def _mark_interrupted(goal: dict[str, Any], message: str) -> dict[str, Any]:
    if goal["status"] != "interrupted":
        _apply_status(goal, "interrupted")
    goal["requires_attention"] = True
    goal["attention_reason"] = "manual_action_required"
    goal["attention_message"] = message
    _semantic_change(goal, history=False)
    _write_goal(goal)
    return goal


def _activate_ready_dependents(completed_goal_id: str) -> None:
    """Wake pending in-process child contexts whose declared dependencies passed."""
    active_workers = sum(
        bool(item.get("status") == "active" and item.get("parent_goal_id"))
        for item in _all_goals()
    )
    for candidate in _all_goals():
        if candidate.get(
            "status"
        ) != "pending" or completed_goal_id not in candidate.get("depends_on", []):
            continue
        if not dependencies_ready(candidate):
            continue
        if active_workers >= MAX_CONCURRENT_GOALS:
            break
        try:
            from agent import AgentContext, UserMessage

            context = AgentContext.get(candidate["context_id"])
            if context is None:
                _mark_interrupted(candidate, "Dependent worker context is unavailable.")
                continue
            context.paused = False
            if not context.is_running():
                context.communicate(
                    UserMessage(message=candidate["objective"], attachments=[])
                )
            if not context.is_running():
                _mark_interrupted(candidate, "Dependent worker did not start.")
                continue
            _apply_status(candidate, "active")
            _semantic_change(candidate, history=False)
            _write_goal(candidate)
            active_workers += 1
        except Exception as error:
            _mark_interrupted(
                candidate, f"Dependent worker start failed: {type(error).__name__}"
            )


def _all_goals() -> list[dict[str, Any]]:
    records = []
    for path in _goals_directory().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("context_id"):
            records.append(_normalize_goal(raw, context_id=str(raw["context_id"])))
    return records


def delete_goal(context_id: str) -> None:
    context_id = _require_context_id(context_id)
    Path(_goal_path(context_id)).unlink(missing_ok=True)
    Path(_legacy_goal_path(context_id)).unlink(missing_ok=True)
    _notify_goal_changed(context_id)


def public_goal(goal: dict[str, Any] | None) -> dict[str, Any] | None:
    if not goal:
        return None
    return {
        key: value
        for key, value in goal.items()
        if key not in {"idempotency_key", "idempotency_scope"}
    }


def summarize_goal(goal: dict[str, Any] | None) -> str:
    if not goal:
        return "No goal is set for this chat."
    lines = [
        f"Goal ID: {goal['goal_id']}",
        f"Status: {goal['status']}",
        f"Goal: {goal['objective']}",
        f"Progress revision: {goal['progress_revision']}",
        f"Active time: {_format_elapsed(_elapsed_seconds(goal))}",
    ]
    if goal.get("current_milestone"):
        lines.append(f"Milestone: {goal['current_milestone']}")
    if goal.get("requires_attention"):
        lines.append(
            f"Attention: {goal.get('attention_reason')}: {goal.get('attention_message')}"
        )
    if goal.get("note"):
        lines.append(f"Note: {goal['note']}")
    return "\n".join(lines)


def _write_goal(goal: dict[str, Any]) -> None:
    path = Path(_goal_path(str(goal["context_id"])))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(goal, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
    _notify_goal_changed(str(goal["context_id"]))


def _notify_goal_changed(context_id: str) -> None:
    from agent import AgentContext

    context = AgentContext.get(context_id)
    if context is None:
        return
    context.set_output_data("_goal_revision", time.time())
    try:
        from helpers.state_monitor_integration import mark_dirty_for_context

        mark_dirty_for_context(context_id, reason="plugins._goal")
    except Exception:
        pass


def _normalize_goal(raw: dict[str, Any], *, context_id: str) -> dict[str, Any]:
    now = _now()
    status = LEGACY_STATUS.get(
        str(raw.get("status") or "active").lower(),
        str(raw.get("status") or "active").lower(),
    )
    status = status if status in VALID_STATUSES else "active"
    goal = {
        "goal_id": str(raw.get("goal_id") or f"goal_{uuid.uuid4().hex}"),
        "context_id": context_id,
        "owner_profile": _clean_text(raw.get("owner_profile")),
        "parent_goal_id": raw.get("parent_goal_id"),
        "title": _clean_text(raw.get("title"))
        or _clean_text(raw.get("objective"))[:120],
        "objective": _clean_objective(raw.get("objective")),
        "success_criteria": _normalize_criteria(raw.get("success_criteria")),
        "constraints": _string_list(raw.get("constraints")),
        "evidence_required": _string_list(raw.get("evidence_required")),
        "autonomy": _normalize_autonomy(raw.get("autonomy")),
        "status": status,
        "current_milestone": _clean_text(raw.get("current_milestone")),
        "goal_revision": max(1, _int(raw.get("goal_revision"), 1)),
        "progress_revision": max(1, _int(raw.get("progress_revision"), 1)),
        "requires_attention": bool(raw.get("requires_attention", False)),
        "attention_reason": _clean_text(raw.get("attention_reason")),
        "attention_message": _clean_text(raw.get("attention_message")),
        "last_checkpoint": raw.get("last_checkpoint")
        if isinstance(raw.get("last_checkpoint"), dict)
        else {},
        "result": raw.get("result") if isinstance(raw.get("result"), dict) else {},
        "children": _string_list(raw.get("children")),
        "depends_on": _string_list(raw.get("depends_on")),
        "depth": max(0, _int(raw.get("depth"), 0)),
        "idempotency_key": _clean_text(raw.get("idempotency_key")),
        "idempotency_scope": _clean_text(raw.get("idempotency_scope")),
        "history": raw.get("history")[-MAX_HISTORY:]
        if isinstance(raw.get("history"), list)
        else [],
        "created_by": _clean_created_by(raw.get("created_by")),
        "token_budget": _clean_token_budget(raw.get("token_budget")),
        "created_at": str(raw.get("created_at") or now),
        "active_since": str(raw.get("active_since") or ""),
        "elapsed_seconds": _clean_elapsed_seconds(raw.get("elapsed_seconds")),
        "updated_at": str(raw.get("updated_at") or now),
        "note": _clean_text(raw.get("note")),
    }
    if status == "active" and not goal["active_since"]:
        goal["active_since"] = goal["created_at"]
    return goal


def _definition(goal):
    return {
        key: goal.get(key)
        for key in (
            "title",
            "objective",
            "success_criteria",
            "constraints",
            "evidence_required",
            "autonomy",
        )
    }


def _semantic_change(goal, *, history=False):
    goal["progress_revision"] = int(goal.get("progress_revision", 0)) + 1
    goal["updated_at"] = _now()


def _apply_criterion_updates(goal, updates):
    changed = False
    mapping = (
        {
            str(x.get("criterion") or x.get("text")): x
            for x in updates
            if isinstance(x, dict)
        }
        if isinstance(updates, list)
        else {}
    )
    for item in goal.get("success_criteria", []):
        update = mapping.get(item["criterion"])
        if update:
            state = str(update.get("state") or "NOT_VERIFIED").upper()
            if state not in CRITERION_STATES:
                raise ValueError("Invalid criterion state")
            evidence = _string_list(update.get("evidence"))
            if (state, evidence) != (item["state"], item["evidence"]):
                item["state"], item["evidence"] = state, evidence
                changed = True
    return changed


def _normalize_criteria(value):
    result = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, str):
            result.append(
                {
                    "criterion": _clean_text(item),
                    "state": "NOT_VERIFIED",
                    "evidence": [],
                }
            )
        elif isinstance(item, dict) and _clean_text(
            item.get("criterion") or item.get("text")
        ):
            state = str(item.get("state") or "NOT_VERIFIED").upper()
            state = state if state in CRITERION_STATES else "NOT_VERIFIED"
            result.append(
                {
                    "criterion": _clean_text(item.get("criterion") or item.get("text")),
                    "state": state,
                    "evidence": _string_list(item.get("evidence")),
                }
            )
    return result


def _normalize_autonomy(value):
    data = value if isinstance(value, dict) else {}
    level = str(data.get("level") or "bounded").lower()
    if level not in AUTONOMY_LEVELS:
        raise ValueError("Invalid autonomy level")
    defaults = {
        "may_modify_code": level in {"implementation", "operational"},
        "may_run_tests": True,
        "may_delegate": level in {"implementation", "operational"},
        "may_create_worktrees": level in {"implementation", "operational"},
        "may_external_write": False,
    }
    return {
        "level": level,
        **{key: bool(data.get(key, default)) for key, default in defaults.items()},
    }


def _find_idempotent(key, scope=""):
    for path in _goals_directory().glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(raw, dict)
            and raw.get("idempotency_key") == key
            and raw.get("idempotency_scope", "") == scope
        ):
            return _normalize_goal(raw, context_id=str(raw.get("context_id") or ""))
    return None


def _required_goal(context_id):
    found = get_goal(context_id)
    if not found:
        raise FileNotFoundError("Goal not found")
    return found


def _goals_directory():
    return Path(
        files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR, PLUGIN_NAME, GOALS_DIR)
    )


def _goal_path(context_id):
    return str(
        _goals_directory()
        / f"{hashlib.sha256(_require_context_id(context_id).encode()).hexdigest()}.json"
    )


def _legacy_goal_path(context_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", context_id).strip("._")[:180]
    if not safe:
        raise ValueError("A chat context is required")
    return str(_goals_directory() / f"{safe}.json")


def _require_context_id(value):
    value = str(value or "").strip()
    if not value:
        raise ValueError("A chat context is required")
    return value


def _required_objective(value):
    value = _clean_objective(value)
    if not value:
        raise ValueError("Goal objective is required")
    return value


def _clean_objective(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_text(value):
    return str(value or "").strip()


def _string_list(value):
    return (
        [_clean_text(x) for x in value]
        if isinstance(value, list)
        else ([_clean_text(value)] if _clean_text(value) else [])
    )


def _normalize_status(value):
    value = LEGACY_STATUS.get(
        str(value or "").strip().lower(), str(value or "").strip().lower()
    )
    if value not in VALID_STATUSES:
        raise ValueError(f"Invalid goal status: {value}")
    return value


def _clean_created_by(value):
    return (
        str(value or "user").lower()
        if str(value or "user").lower() in {"user", "model", "spynel"}
        else "user"
    )


def _clean_token_budget(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _apply_status(goal, status):
    current = goal.get("status", "active")
    if current == "active" and status != "active":
        goal["elapsed_seconds"] = _elapsed_seconds(goal)
        goal["active_since"] = ""
    elif current != "active" and status == "active":
        goal["active_since"] = _now()
    goal["status"] = status


def _elapsed_seconds(goal):
    elapsed = _clean_elapsed_seconds(goal.get("elapsed_seconds"))
    return elapsed + (
        _seconds_between(str(goal.get("active_since") or ""), _now())
        if goal.get("status") == "active"
        else 0
    )


def _clean_elapsed_seconds(value):
    return max(0, _int(value, 0))


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _seconds_between(start, end):
    a, b = _parse_time(start), _parse_time(end)
    return max(0, int((b - a).total_seconds())) if a and b else 0


def _parse_time(value):
    value = str(value or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


def _format_elapsed(seconds):
    hours, rem = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(rem, 60)
    return (
        f"{hours}h {minutes}m"
        if hours
        else f"{minutes}m {seconds}s"
        if minutes
        else f"{seconds}s"
    )


def _now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
