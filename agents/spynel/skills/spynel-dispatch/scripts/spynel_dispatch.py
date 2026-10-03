#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

PROFILE_RE = re.compile(r"(?<!\S)@([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)")
SDK_RE = re.compile(r"(?<!\S)/([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)")
PENDING = {"queued", "pending", "running", "waiting", "processing", "accepted"}
DONE = {"completed", "complete", "done", "succeeded", "success", "finished"}
FAILED = {"failed", "error", "cancelled", "canceled", "timeout"}


@dataclass
class Route:
    profile: str | None
    sdk: str | None
    message: str


def parse_route(text: str) -> Route:
    p = PROFILE_RE.search(text)
    s = SDK_RE.search(text)
    cleaned = PROFILE_RE.sub(" ", text, count=1)
    cleaned = SDK_RE.sub(" ", cleaned, count=1)
    return Route(p.group(1).lower() if p else None, s.group(1).lower() if s else None, " ".join(cleaned.split()))


def _https_url(value: str, label: str) -> str:
    u = urlparse(value.strip())
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise ValueError(f"{label} must be a credential-free HTTPS URL")
    return value.rstrip("/")


def _env_key(prefix: str, name: str) -> str:
    return f"SPYNEL_{prefix}_{re.sub(r'[^A-Z0-9]+', '_', name.upper())}_URL"


def resolve_external(route: Route) -> tuple[str, str] | None:
    # /sdk is always an external HTTPS gateway. @profile is external only when
    # explicitly registered in the environment; otherwise it can be delegated
    # internally by Agent Zero in a fresh context.
    if route.sdk:
        key = _env_key("SDK", route.sdk)
        raw = os.getenv(key, "")
        if not raw:
            raise KeyError(f"Unknown SDK '/{route.sdk}'; configure {key}")
        return _https_url(raw, key), key
    if route.profile:
        key = _env_key("AGENT", route.profile)
        raw = os.getenv(key, "")
        if raw:
            return _https_url(raw, key), key
    return None


async def _curl_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, Any, str]:
    body = json.dumps(payload, ensure_ascii=False).encode()
    proc = await asyncio.create_subprocess_exec(
        "curl", "--silent", "--show-error", "--fail-with-body",
        "--proto", "=https", "--proto-redir", "=https",
        "--connect-timeout", str(min(timeout, 20)), "--max-time", str(timeout),
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "-X", "POST", "--data-binary", "@-", "--write-out", "\n%{http_code}", url,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(body), timeout=timeout + 5)
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 3)
        except asyncio.TimeoutError:
            proc.kill(); await proc.wait()
        raise TimeoutError(f"request timed out after {timeout}s")
    text = out.decode(errors="replace")
    response_text, _, code_text = text.rpartition("\n")
    code = int(code_text) if code_text.isdigit() else 0
    try:
        data: Any = json.loads(response_text) if response_text.strip() else {}
    except json.JSONDecodeError:
        data = {"text": response_text}
    return code, data, err.decode(errors="replace").strip()


async def _curl_get(url: str, timeout: float) -> tuple[int, Any, str]:
    proc = await asyncio.create_subprocess_exec(
        "curl", "--silent", "--show-error", "--fail-with-body",
        "--proto", "=https", "--proto-redir", "=https",
        "--connect-timeout", str(min(timeout, 20)), "--max-time", str(timeout),
        "-H", "Accept: application/json", "--write-out", "\n%{http_code}", url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
    text = out.decode(errors="replace")
    response_text, _, code_text = text.rpartition("\n")
    code = int(code_text) if code_text.isdigit() else 0
    try: data = json.loads(response_text) if response_text.strip() else {}
    except json.JSONDecodeError: data = {"text": response_text}
    return code, data, err.decode(errors="replace").strip()


def _state(data: Any) -> str:
    if not isinstance(data, dict): return ""
    value = data.get("state") or data.get("status") or ""
    return str(value).strip().lower()


def _poll_url(data: Any) -> str | None:
    if not isinstance(data, dict): return None
    value = data.get("poll_url") or data.get("status_url")
    return str(value).strip() if value else None


async def dispatch(text: str, *, timeout: float, poll_interval: float) -> dict[str, Any]:
    route = parse_route(text)
    events: list[dict[str, Any]] = [{"state": "parsed", "profile": route.profile, "sdk": route.sdk}]
    if not route.profile and not route.sdk:
        return {"mode": "local", "message": route.message, "events": events + [{"state": "local"}]}

    external = resolve_external(route)
    if external is None:
        return {"mode": "internal", "profile": route.profile, "message": route.message,
                "events": events + [{"state": "internal_profile", "detail": "create fresh Agent Zero chat context; do not create a profile"}]}

    url, registry_key = external
    events.append({"state": "dispatching", "target": registry_key})
    payload = {"message": route.message, "agent_profile": route.profile, "agent_sdk": route.sdk}
    code, data, stderr = await _curl_json(url, payload, timeout)
    events.append({"state": "sent", "http_status": code})
    if code < 200 or code >= 300:
        return {"mode": "external", "ok": False, "state": "failed", "error": stderr or data, "events": events}

    state = _state(data)
    poll_url = _poll_url(data)
    if (code == 202 or state in PENDING) and poll_url:
        poll_url = _https_url(poll_url, "poll_url")
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            events.append({"state": "waiting"})
            await asyncio.sleep(max(0.25, poll_interval))
            pcode, pdata, perr = await _curl_get(poll_url, min(30, timeout))
            state = _state(pdata)
            events.append({"state": "polling", "http_status": pcode, "remote_state": state or None})
            if pcode < 200 or pcode >= 300:
                return {"mode": "external", "ok": False, "state": "failed", "error": perr or pdata, "events": events}
            data = pdata
            if state in DONE: break
            if state in FAILED:
                return {"mode": "external", "ok": False, "state": state, "response": data, "events": events}
        else:
            return {"mode": "external", "ok": False, "state": "timeout", "events": events}

    events.append({"state": "completed"})
    return {"mode": "external", "ok": True, "state": "completed", "response": data, "events": events}


async def amain() -> int:
    ap = argparse.ArgumentParser(description="Spynel HTTPS dispatcher")
    ap.add_argument("message", nargs="?", help="message containing optional @profile and /sdk")
    ap.add_argument("--timeout", type=float, default=float(os.getenv("SPYNEL_REQUEST_TIMEOUT", "300")))
    ap.add_argument("--poll-interval", type=float, default=float(os.getenv("SPYNEL_POLL_INTERVAL", "2")))
    ns = ap.parse_args()
    text = ns.message if ns.message is not None else sys.stdin.read()
    try:
        result = await dispatch(text, timeout=max(1, ns.timeout), poll_interval=max(.25, ns.poll_interval))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok", True) else 2
    except Exception as exc:
        print(json.dumps({"ok": False, "state": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain()))
