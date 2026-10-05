from __future__ import annotations
import json
from typing import Any
from plugins._goal.tools import goal

def run(payload: dict[str, Any]) -> dict[str, Any]:
    invocation=payload.get("invocation") or {}; raw=str(invocation.get("raw_arguments") or "").strip(); tokens=((invocation.get("arguments") or {}).get("tokens") or [])
    context_id=str((payload.get("context") or {}).get("context_id") or "").strip()
    if not context_id:return _effects(_toast("Open or create a chat context first.",level="error"))
    action=str(tokens[0] if tokens else "").lower()
    remainder=raw.split(None,1)[1].strip() if len(tokens)>1 else ""
    try:
        if action in {"","status","show"}:return _show_markdown("Goal",goal.summarize_goal(goal.get_goal(context_id)))
        if action=="set": return _changed("Goal set.",goal.create_goal(context_id,remainder,created_by="user"),send_text=remainder)
        if action in {"pause","paused"}:return _changed("Goal paused.",goal.update_goal(context_id,status="paused"))
        if action in {"resume","start","active"}:return _changed("Goal resumed.",goal.update_goal(context_id,status="active"))
        if action in {"cancel","delete","clear","remove"}:
            if action=="cancel": return _changed("Goal cancelled.",goal.update_goal(context_id,status="cancelled"))
            goal.delete_goal(context_id);return _changed("Goal deleted.",None)
        if action in {"complete","done"}:return _changed("Goal completion evaluated.",goal.complete_goal(context_id))
        if action=="blocked":return _changed("Goal blocked.",goal.update_goal(context_id,status="blocked",note=remainder,requires_attention=True,attention_reason="repeated_failure"))
        if action in {"edit","revise"}:return _changed("Goal revised.",goal.revise_goal(context_id,objective=remainder))
        if action=="checkpoint":return _changed("Goal checkpoint saved.",goal.checkpoint_goal(context_id,note=remainder))
        if action=="subgoal":
            parts=remainder.split(None,1)
            if len(parts)!=2: raise ValueError("Usage: /goal subgoal @profile objective")
            child=goal.create_subgoal_context(context_id,parts[0],parts[1])
            return _effects(_toast("Subgoal created."),{"type":"goal_changed","goal":goal.public_goal(goal.get_goal(context_id))},{"type":"show_markdown","title":"Subgoal","content":goal.summarize_goal(child)})
        if action in {"auto","ask","model"}:return _auto_prompt(remainder)
        current=goal.create_goal(context_id,raw,created_by="user");return _changed("Goal set.",current,send_text=raw)
    except FileNotFoundError:return _effects(_toast("No goal is set for this chat.",level="error"))
    except ValueError as error:return _effects(_toast(str(error),level="error"))

def _auto_prompt(hint):
    prompt="Create and own a durable goal for this chat. Derive milestones, persist semantic checkpoints, delegate bounded child goals, and complete only from evidence."
    if hint:prompt+=f"\n\nUser hint: {hint}"
    return {"text":prompt,"effects":[]}
def _changed(message,current_goal,*,send_text=""):return _effects(_toast(message),{"type":"goal_changed","goal":goal.public_goal(current_goal)},{"type":"send_message","text":send_text} if send_text else {})
def _effects(*effects):return {"text":"","effects":[item for item in effects if item]}
def _toast(message,*,level="success"):return {"type":"toast","message":message,"level":level}
def _show_markdown(title,content):return _effects({"type":"show_markdown","title":title,"content":content})
