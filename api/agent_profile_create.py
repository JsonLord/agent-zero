from __future__ import annotations

import re

from helpers import subagents
from helpers.api import ApiHandler, Request, Response


_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_RESERVED = {"agent0", "default", "_example"}


class CreateAgentProfile(ApiHandler):
    """Create a user-owned agent profile under usr/agents.

    This endpoint is intentionally narrow: callers may define metadata and prompt
    overrides, but never an arbitrary filesystem path. Built-in/reserved profiles
    cannot be replaced.
    """

    async def process(self, input: dict, request: Request) -> dict | Response:
        name = str(input.get("name", "") or "").strip()
        if not _PROFILE_RE.fullmatch(name) or name.startswith("_"):
            return Response(
                status=400,
                response=(
                    "Invalid profile name. Use 1-64 letters, digits, '-' or '_', "
                    "starting with a letter or digit."
                ),
            )
        if name.lower() in _RESERVED:
            return Response(status=409, response=f"Profile '{name}' is reserved")

        existing = subagents.get_agents_dict()
        if name in existing:
            return Response(status=409, response=f"Profile '{name}' already exists")

        title = str(input.get("title", name) or name).strip()[:120]
        description = str(input.get("description", "") or "").strip()[:1000]
        context = str(input.get("context", "") or "")
        prompts_in = input.get("prompts") or {}
        if not isinstance(prompts_in, dict):
            return Response(status=400, response="prompts must be an object")

        prompts: dict[str, str] = {}
        for key, value in prompts_in.items():
            key_s = str(key or "").strip()
            if not key_s or len(key_s) > 160:
                return Response(status=400, response="Invalid prompt filename")
            prompts[key_s] = str(value or "")

        profile = subagents.SubAgent(
            name=name,
            title=title,
            description=description,
            context=context,
            enabled=bool(input.get("enabled", True)),
            prompts=prompts,
        )
        subagents.save_agent_data(name, profile)
        return {
            "ok": True,
            "agent_profile": name,
            "agent_profile_label": title or name,
            "origin": "user",
        }
