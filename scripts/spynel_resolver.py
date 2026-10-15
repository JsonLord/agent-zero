#!/usr/bin/env python3
"""Read-only, fail-closed Spynel recognition; no dispatch or model imports at import time."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "coding agent": "developer",
    "repo manager": "repository-manager",
    "prompt improver": "prompt-improver",
    "gepa specialist": "prompt-improver",
}
TOKEN = re.compile(r"(?<!\S)([@/])([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)")
# Mask examples without changing offsets in the original message.
EXCLUDED = re.compile(
    r'```[\s\S]*?(?:```|$)|`[^`\n]*`|"[^"\n]*"|\'[^\'\n]*\'|https?://\S+|(?:^|\n)\s*>[^\n]*'
)
INTENT = re.compile(
    r"(?:^|[.!?\n]\s*|\b(?:and|or)\s+)(?:please\s+)?(?:ask|have|let|tell|use|delegate\s+to)\s+(?:the\s+)?",
    re.IGNORECASE,
)


def visible(text):
    return EXCLUDED.sub(lambda m: " " * len(m.group()), text)


def normalize(value):
    return re.sub(r"[-_\s]+", " ", value).strip().casefold()


def discover(project=None):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from helpers import subagents

    profiles = {
        key: item.title
        for key, item in subagents.get_available_agents_dict(project).items()
    }
    external = {}
    for key, value in os.environ.items():
        match = re.fullmatch(r"SPYNEL_(SDK|AGENT)_([A-Z0-9_]+)_URL", key)
        if not match or not value:
            continue
        parsed = urlparse(value)
        if (
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
        ):
            kind, name = match.groups()
            external[
                (
                    "sdk" if kind == "SDK" else "external_agent",
                    name.lower().replace("_", "-"),
                )
            ] = name
    return profiles, external


def workspace_candidates(text, root):
    root = Path(root).resolve()
    found = set()
    # Require path-oriented language or a delegation request; plain mentions do
    # not establish workspace intent. Never scan/create user directories.
    if not (
        INTENT.search(text)
        or re.search(
            r"\b(?:work on|folder|directory|workspace|inspect)\b", text, re.IGNORECASE
        )
    ):
        return []
    for word in re.findall(r"(?<![\w./-])[\w.-]+(?:/[\w.-]+)*(?![\w./-])", text):
        word = word.rstrip(".") if word not in {".", ".."} else word
        try:
            candidate = (root / word).resolve()
            if (
                candidate != root
                and candidate.is_relative_to(root)
                and candidate.is_dir()
            ):
                found.add(str(candidate))
        except (OSError, RuntimeError):
            continue
    return sorted(found)


def resolve(text, profiles, external=None, workspace_root="/a0/usr/workdir"):
    external = external or {}
    clean = visible(text)
    workspaces = workspace_candidates(clean, workspace_root)
    base = {
        "decision": "local",
        "target_type": None,
        "target_id": None,
        "workspace_path": workspaces[0] if len(workspaces) == 1 else None,
        "recognition": "deterministic",
        "ambiguous": len(workspaces) > 1,
        "message": text,
        "workspace_candidates": workspaces,
    }
    aliases = {}

    def add(label, target):
        aliases.setdefault(normalize(label), set()).add(target)

    for name, title in profiles.items():
        add(name, ("internal_agent", name))
        add(title, ("internal_agent", name))
    for alias, name in ALIASES.items():
        if name in profiles:
            add(alias, ("internal_agent", name))
    for target, title in external.items():
        # An environment-registered agent overrides its internal counterpart.
        if target[0] == "external_agent":
            for values in aliases.values():
                values.discard(("internal_agent", target[1]))
        add(target[1], target)
        add(title, target)
    explicit = list(TOKEN.finditer(clean))
    targets = set()
    if explicit:
        # Preserve historical @profile + /sdk combination: SDK selects gateway.
        selected = [m for m in explicit if m[1] == "/"] or explicit
        for match in selected:
            name = match[2].lower()
            target = (
                ("sdk", name)
                if match[1] == "/"
                else ("external_agent", name)
                if ("external_agent", name) in external
                else ("internal_agent", name)
            )
            if (
                target[0] == "internal_agent"
                and name not in profiles
                or target[0] != "internal_agent"
                and target not in external
            ):
                return {**base, "decision": "abstain", "reason": "unknown_target"}
            targets.add(target)
    else:
        for intent in INTENT.finditer(clean):
            rest = clean[intent.end() :]
            matches = []
            for label, values in aliases.items():
                pattern = r"[-_\s]+".join(re.escape(word) for word in label.split())
                match = re.match(pattern + r"(?=$|[\s,.!?;:])", rest, re.IGNORECASE)
                if match:
                    matches.append((match.end(), values))
            if matches:
                longest = max(length for length, _ in matches)
                for length, values in matches:
                    if length == longest:
                        tail = rest[length:]
                        if re.match(r"\.\w", tail):
                            continue
                        if re.match(r"\s+(?:and|or)\s+", tail, re.IGNORECASE):
                            return {
                                **base,
                                "decision": "abstain",
                                "ambiguous": True,
                                "reason": "multiple_targets",
                            }
                        targets.update(values)
            else:
                return {**base, "decision": "abstain", "reason": "unknown_target"}
    if len(targets) > 1 or len(workspaces) > 1:
        return {**base, "decision": "abstain", "ambiguous": True, "reason": "ambiguous"}
    if targets:
        kind, name = targets.pop()
        return {**base, "decision": "dispatch", "target_type": kind, "target_id": name}
    return base


class Classifier(Protocol):
    async def classify(self, message: str, candidates: list[dict]) -> dict:
        """Return {decision: abstain} or an exact candidate object."""
        ...


async def classify_ambiguous(
    classifier: Classifier, message, candidates, *, enabled=False, timeout=3
):
    """Opt-in interface; never permit classifier-created targets or paths."""
    abstain = {"decision": "abstain"}
    if not enabled or not candidates:
        return abstain
    try:
        result = await asyncio.wait_for(
            classifier.classify(message, candidates), min(10, max(0.1, timeout))
        )
        return result if result in candidates else abstain
    except Exception:  # noqa: BLE001 - external classifier boundary must fail closed
        return abstain


class HTTPSClassifier:
    """Optional remote Laya adapter. No local inference dependencies."""

    def __init__(self, endpoint):
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Classifier requires a credential-free HTTPS endpoint")
        self.endpoint = endpoint

    async def classify(self, message, candidates):
        import aiohttp

        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3, connect=1)
            ) as session,
            session.post(
                self.endpoint,
                json={"message": message, "candidates": candidates},
                allow_redirects=False,
            ) as response,
        ):
            if response.status != 200:
                return {"decision": "abstain"}
            return await response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolve-only", action="store_true", required=True)
    parser.add_argument("--workspace-root", default="/a0/usr/workdir")
    parser.add_argument("--project")
    parser.add_argument("message")
    args = parser.parse_args()
    profiles, external = discover(args.project)
    print(
        json.dumps(
            resolve(args.message, profiles, external, args.workspace_root),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
