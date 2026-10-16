#!/usr/bin/env python3
"""Read-only, fail-closed Spynel recognition; no dispatch or model imports at import time."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
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
    r'```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]*`|"[^"\n]*"|\'[^\'\n]*\'|(?:[a-z][a-z0-9+.-]*://|www\.)\S+|(?:^|\n)\s*>[^\n]*'
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


def resolve(
    text,
    profiles,
    external=None,
    workspace_root="/a0/usr/workdir",
    *,
    match_workspace=True,
):
    """Recognize a candidate; only prepare_route validates it for execution."""
    external = external or {}
    clean = visible(text)
    workspaces = workspace_candidates(clean, workspace_root) if match_workspace else []
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
                if ("internal_agent", target[1]) in values:
                    values.discard(("internal_agent", target[1]))
                    values.add(target)
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


def load_workspace_aliases():
    """Optional trusted JSON configuration; user/model text cannot define aliases."""
    value = json.loads(os.getenv("SPYNEL_WORKSPACE_ALIASES", "{}"))
    if not isinstance(value, dict) or any(
        not isinstance(k, str)
        or not k.strip()
        or not isinstance(v, str)
        or not v.strip()
        for k, v in value.items()
    ):
        raise ValueError("SPYNEL_WORKSPACE_ALIASES must map names to existing paths")
    normalized = {normalize(k): v for k, v in value.items()}
    if len(normalized) != len(value):
        raise ValueError("Ambiguous workspace aliases")
    return normalized


def _target_spans(text, profiles, external):
    spans = [m.span() for m in TOKEN.finditer(text)]
    labels = [
        *profiles,
        *profiles.values(),
        *(key[1] for key in external),
        *external.values(),
        *ALIASES,
    ]
    for intent in INTENT.finditer(text):
        for label in labels:
            pattern = r"[-_\s]+".join(
                re.escape(part) for part in normalize(label).split()
            )
            match = re.match(
                pattern + r"(?=$|[\s,.!?;:])", text[intent.end() :], re.IGNORECASE
            )
            if match:
                spans.append((intent.end(), intent.end() + match.end()))
    return spans


def workspace_context(text, root, *, aliases=None, selected=None, target_spans=()):
    """Validate referenced directories AND files, retaining no unverified path."""
    root = Path(root).resolve()
    aliases = aliases or {}
    clean = visible(text)
    directories, files, errors = set(), set(), []

    def add(raw, required):
        raw = raw.rstrip(".,;:!?")
        if not raw or raw in {".", ".."}:
            if required:
                errors.append("workspace_invalid")
            return
        value = aliases.get(normalize(raw), raw)
        required = required or (root / value).is_symlink()
        try:
            candidate = (root / value).resolve(strict=True)
            if not candidate.is_relative_to(root):
                if required or (root / value).exists():
                    errors.append("workspace_escape")
                return
            if candidate.is_dir():
                if candidate != root or required:
                    directories.add(str(candidate))
            elif candidate.is_file():
                files.add(str(candidate))
            elif required:
                errors.append("workspace_invalid")
        except (OSError, RuntimeError, ValueError):
            if required:
                errors.append("workspace_missing")

    if selected is not None:
        add(selected, True)
    used = list(target_spans)
    # Multiword aliases are configured, never guessed by a model.
    for alias in sorted(aliases, key=len, reverse=True):
        pattern = (
            r"(?<![\w/-])"
            + r"[-_\s]+".join(re.escape(p) for p in alias.split())
            + r"(?![\w/-])"
        )
        for match in re.finditer(pattern, clean, re.IGNORECASE):
            if not any(
                match.start() < end and match.end() > start for start, end in used
            ):
                add(alias, True)
                used.append(match.span())
    for match in re.finditer(
        r"(?<![\w./-])(?:/[\w./-]+|[\w.-]+(?:/[\w.-]+)*)(?![\w./-])", clean
    ):
        if any(match.start() < end and match.end() > start for start, end in used):
            continue
        word = match.group().rstrip(".,;:!?")
        before, after = clean[: match.start()], clean[match.end() :]
        required = (
            "/" in word
            or bool(re.search(r"\.[A-Za-z0-9]{1,8}$", word))
            or bool(
                re.search(
                    r"\b(?:file|folder|directory|workspace)\s+(?:the\s+)?$",
                    before,
                    re.IGNORECASE,
                )
            )
            or (
                bool(re.match(r"\s+(?:file|folder|directory)\b", after, re.IGNORECASE))
                and word.casefold()
                not in {"inspect", "check", "fix", "work", "on", "use", "in"}
            )
            or (
                "-" in word
                and bool(
                    re.search(
                        r"\b(?:inspect|check|fix|work on)\s+$", before, re.IGNORECASE
                    )
                )
            )
        )
        # Syntax words themselves are not path references.
        if word.casefold() not in {"file", "folder", "directory", "workspace", "the"}:
            add(word, required)
    # Quoted paths are allowed only after a visible path marker, not within
    # quoted examples or fenced source code.
    for match in re.finditer(
        r"""\b(?:file|folder|directory|workspace)\s+["']([^"'\n]+)["']""",
        text,
        re.IGNORECASE,
    ):
        if clean[match.start()] != " ":
            add(match[1], True)
    path = None
    if len(directories) > 1:
        errors.append("workspace_ambiguous")
    elif directories:
        path = next(iter(directories))
        if any(not Path(file).is_relative_to(path) for file in files):
            errors.append("workspace_ambiguous")
    elif files:
        parents = {str(Path(file).parent) for file in files}
        if len(parents) == 1:
            path = parents.pop()
        else:
            errors.append("workspace_ambiguous")
    return {
        "workspace_path": path if not errors else None,
        "workspace_files": sorted(files) if not errors else [],
        "workspace_candidates": sorted(directories),
        "workspace_error": errors[0] if errors else None,
    }


def prepare_route(
    text,
    profiles,
    external=None,
    workspace_root="/a0/usr/workdir",
    *,
    profile=None,
    sdk=None,
    workspace=None,
    workspace_aliases=None,
):
    """Final deterministic validation for recognized or main-model-selected work.

    No model call is made. Explicit tokens beat selections; a selected identifier
    cannot override an unknown or ambiguous natural-language destination.
    """
    external = external or {}
    result = resolve(text, profiles, external, workspace_root, match_workspace=False)
    clean = visible(text)
    explicit = list(TOKEN.finditer(clean))
    explicit_profiles = {m[2].lower() for m in explicit if m[1] == "@"}
    explicit_sdks = {m[2].lower() for m in explicit if m[1] == "/"}
    if len(explicit_profiles) > 1 or len(explicit_sdks) > 1:
        result = {
            **result,
            "decision": "abstain",
            "reason": "ambiguous",
            "ambiguous": True,
        }
    # Validate all identifiers, even @profile accompanying a /sdk gateway.
    for name in explicit_profiles:
        if name not in profiles and ("external_agent", name) not in external:
            return {**result, "decision": "abstain", "reason": "unknown_profile"}
    for name in explicit_sdks:
        if ("sdk", name) not in external:
            return {**result, "decision": "abstain", "reason": "unknown_sdk"}
    if not explicit and result["decision"] == "local" and (profile or sdk):
        # Ordinary interpretation happens in Spynel's EXISTING main interaction.
        # This API only validates its proposed identifiers; it never classifies.
        if not clean.strip():
            return {**result, "decision": "abstain", "reason": "no_instruction"}
        if (
            profile
            and profile not in profiles
            and ("external_agent", profile) not in external
        ):
            return {**result, "decision": "abstain", "reason": "unknown_profile"}
        if sdk and ("sdk", sdk) not in external:
            return {**result, "decision": "abstain", "reason": "unknown_sdk"}
        kind = (
            "sdk"
            if sdk
            else "external_agent"
            if ("external_agent", profile) in external
            else "internal_agent"
        )
        result = {
            **result,
            "decision": "dispatch",
            "target_type": kind,
            "target_id": sdk or profile,
            "recognition": "validated_selection",
        }
    if result["decision"] == "abstain" and result.get("reason") != "ambiguous":
        return result
    paths = workspace_context(
        text,
        workspace_root,
        aliases=workspace_aliases,
        selected=workspace,
        target_spans=_target_spans(clean, profiles, external),
    )
    result = {**result, **paths}
    if paths["workspace_error"]:
        return {
            **result,
            "decision": "abstain",
            "reason": paths["workspace_error"],
            "ambiguous": paths["workspace_error"] == "workspace_ambiguous",
        }
    result["explicit_profile"] = next(iter(explicit_profiles), None)
    result["agent_profile"] = result["explicit_profile"] or (
        profile if result.get("recognition") == "validated_selection" else None
    )
    return result


def profile_override_conflicts(agent):
    """Read-only audit of active higher-priority Spynel instructions and skills.

    Metadata-only title/avatar changes and byte-equivalent copies are allowed.
    Divergent routing instructions block use until the operator reconciles them.
    Never delete, migrate or print local prompt contents.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from helpers import subagents

    bundled = ROOT / "agents/spynel"
    conflicts = []
    for location in subagents.get_paths(
        agent, include_default=False, include_user=False
    ):
        location = Path(location)
        if location.resolve() == bundled.resolve():
            break
        candidates = [
            *location.glob("prompts/agent.system.main*.md"),
            *location.glob("skills/spynel-dispatch/**/*"),
            *location.glob("extensions/**/*.py"),
        ]
        for path in candidates:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            counterpart = bundled / path.relative_to(location)
            try:
                if (
                    not counterpart.is_file()
                    or path.read_bytes() != counterpart.read_bytes()
                ):
                    conflicts.append(str(path))
            except OSError:
                conflicts.append(str(path))
        for name in ("agent.yaml", "agent.json", "_context.md"):
            path = location / name
            if not path.is_file():
                continue
            try:
                if name == "_context.md":
                    context = path.read_text().strip()
                elif name.endswith("json"):
                    context = json.loads(path.read_text()).get("context", "")
                else:
                    from helpers import yaml as yaml_helper

                    context = (yaml_helper.loads(path.read_text()) or {}).get(
                        "context", ""
                    )
                if context:
                    conflicts.append(str(path))
            except (OSError, ValueError, AttributeError):
                conflicts.append(str(path))
    return sorted(set(conflicts))


def profile_conflicts(project=None):
    from types import SimpleNamespace

    agent = SimpleNamespace(
        config=SimpleNamespace(profile="spynel"),
        context=SimpleNamespace(get_data=lambda key: project),
    )
    return profile_override_conflicts(agent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--resolve-only", action="store_true")
    mode.add_argument("--check-profile", action="store_true")
    parser.add_argument("--profile")
    parser.add_argument("--sdk")
    parser.add_argument("--workspace")
    parser.add_argument("--workspace-root", default="/a0/usr/workdir")
    parser.add_argument("--project")
    parser.add_argument("message", nargs="?", default="")
    args = parser.parse_args()
    if args.check_profile:
        conflicts = profile_conflicts(args.project)
        print(
            json.dumps(
                {"status": "blocked" if conflicts else "ok", "conflicts": conflicts}
            )
        )
        return 2 if conflicts else 0
    profiles, external = discover(args.project)
    print(
        json.dumps(
            prepare_route(
                args.message,
                profiles,
                external,
                args.workspace_root,
                profile=args.profile,
                sdk=args.sdk,
                workspace=args.workspace,
                workspace_aliases=load_workspace_aliases(),
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
