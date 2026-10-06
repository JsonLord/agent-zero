#!/usr/bin/env python3
"""Secret-safe, non-destructive OpenOperator Hugging Face acceptance smoke."""

from __future__ import annotations
import json
import os
import argparse
import time
import urllib.error
import urllib.request
import uuid

BASE = os.getenv(
    "OPENOPERATOR_BASE_URL", "https://leon4gr45-openoperator.hf.space"
).rstrip("/")
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
API_KEY = os.getenv("SPYNEL_AGENT_ZERO_API_KEY", "").strip()
TIMEOUT = float(os.getenv("OPENOPERATOR_SMOKE_TIMEOUT", "30"))
POLL = float(os.getenv("SPYNEL_POLL_INTERVAL", "2"))
results = []
REQUIRED_PROFILES = {
    "developer",
    "hacker",
    "spynel",
    "reviewer",
    "tester",
    "tiny-coder",
    "debugger",
    "integrator",
    "frontend-qa",
    "evals",
    "shipper",
    "launch",
    "performance",
    "security",
    "refactorer",
    "maintainer",
    "data-engineer",
    "docs",
}

CRITICAL_SKILLS = {
    "colab-execute",
    "golive",
    "brag",
    "playwright",
    "hf-space",
    "test-evidence",
    "api-contract",
    "benchmark",
    "compile-check",
    "context-packager",
    "dependency-doctor",
    "diff-self-review",
    "docker-diagnose",
    "failure-to-next-patch",
    "git-worktree",
    "github-pr",
    "patch-small",
    "repo-map",
    "secret-safe-env",
    "spec-check",
    "symbol-locator",
    "task-slicer",
    "test-targeted",
}


def request(path, payload=None, *, api=False):
    headers = {"Accept": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = "Bearer " + HF_TOKEN
    if api:
        if not API_KEY:
            raise RuntimeError("SPYNEL_AGENT_ZERO_API_KEY is not configured")
        headers["X-API-KEY"] = API_KEY
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode(errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": "HTTP error"}


def report(name, state, detail=""):
    results.append((name, state))
    print(f"{name}: {state}" + (f" ({detail})" if detail else ""))


def poll(context_id, *, include_logs=False):
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        code, data = request(
            "/api/api_poll",
            {"context_id": context_id, "include_logs": include_logs},
            api=True,
        )
        if code != 200:
            return False, data
        if data.get("requires_attention"):
            return False, data
        if data.get("status") in {"completed", "complete"}:
            if include_logs:
                time.sleep(max(0.25, min(2.0, POLL)))
                final_code, final_data = request(
                    "/api/api_poll",
                    {"context_id": context_id, "include_logs": True},
                    api=True,
                )
                if final_code == 200:
                    data = final_data
            return True, data
        if data.get("status") in {
            "failed",
            "blocked",
            "cancelled",
            "partially_verified",
        }:
            return False, data
        time.sleep(max(0.25, min(POLL, float(data.get("next_poll_after") or POLL))))
    return False, {"error": "finite timeout"}


def _names(value):
    """Extract public catalog names without depending on a single response shape."""
    if isinstance(value, dict):
        value = value.get("data", value.get("skills", value.get("agents", [])))
    if not isinstance(value, list):
        return set()
    return {
        str((item.get("name") or item.get("key")) if isinstance(item, dict) else item)
        .strip()
        .lower()
        for item in value
        if ((item.get("name") or item.get("key")) if isinstance(item, dict) else item)
    }


def discover():
    """Use existing read-only authenticated catalogs; never mutate for discovery."""
    code, agents = request("/api/agents", {"action": "list"}, api=True)
    names = _names(agents)
    missing_profiles = REQUIRED_PROFILES - names
    report(
        "specialist profiles",
        "PASS" if code == 200 and not missing_profiles else "FAIL",
        f"missing: {sorted(missing_profiles)}" if missing_profiles else f"{len(names)} profiles cataloged",
    )
    report("Spynel", "PASS" if "spynel" in names else "FAIL")

    code, skills = request(
        "/api/plugins/_skills/skills_catalog", {"action": "list"}, api=True
    )
    skill_names = _names(skills)
    missing_skills = CRITICAL_SKILLS - skill_names
    report(
        "required skills",
        "PASS" if code == 200 and not missing_skills else "FAIL",
        f"missing: {sorted(missing_skills)}" if missing_skills else f"{len(skill_names)} skills cataloged",
    )


def _settings_acceptance(data):
    additional = data.get("additional", {})
    configured = data.get("settings", {})
    runtime = data.get("runtime", {})
    model = data.get("main_model", {})
    report("settings", "PASS")
    report(
        "runtime",
        "PASS"
        if additional.get("is_dockerized")
        and not additional.get("is_development", False)
        else "FAIL",
        "dockerized production expected",
    )
    report(
        "non-root",
        "PASS"
        if runtime.get("uid") not in {None, 0} and runtime.get("gid") not in {None, 0}
        else "FAIL",
        "non-root uid/gid expected",
    )
    report(
        "root password capability",
        "PASS" if additional.get("root_password_supported") is False else "FAIL",
        "unsupported expected",
    )
    serialized = json.dumps(data)
    report(
        "API key",
        "PASS"
        if configured.get("mcp_server_token") == "************"
        and "BLABLADOR_API_KEY" not in serialized
        else "FAIL",
        "configured/masked",
    )
    report(
        "compatible provider",
        "PASS"
        if model.get("provider") == "other"
        and model.get("name")
        and model.get("api_base")
        else "FAIL",
    )


def _reversible_settings_smoke(data):
    original = data.get("settings", {}).get("time_format")
    alternate = "24h" if original == "12h" else "12h"
    code, changed = request(
        "/api/settings_probe",
        {"action": "set_time_format", "value": alternate},
        api=True,
    )
    code2, reloaded = request("/api/settings_probe", {"action": "get"}, api=True)
    persisted = (
        code == 200
        and code2 == 200
        and reloaded.get("settings", {}).get("time_format") == alternate
    )
    restore_code, _ = request(
        "/api/settings_probe",
        {"action": "set_time_format", "value": original},
        api=True,
    )
    restore_get, restored = request("/api/settings_probe", {"action": "get"}, api=True)
    restored_ok = (
        restore_code == 200
        and restore_get == 200
        and restored.get("settings", {}).get("time_format") == original
    )
    report(
        "settings persistence",
        "PASS" if persisted and restored_ok else "FAIL",
        "safe setting changed, reloaded, and restored",
    )


def main(mode="full"):
    code, data = request("/health")
    report("health", "PASS" if code == 200 and data.get("status") == "ok" else "FAIL")
    if mode == "basic":
        return 1 if any(state != "PASS" for _, state in results) else 0
    if API_KEY:
        code, data = request("/api/settings_probe", {"action": "get"}, api=True)
        if code == 200:
            _settings_acceptance(data)
            if mode == "full":
                _reversible_settings_smoke(data)
        else:
            report("settings", "FAIL", "authenticated settings probe failed")
    else:
        report("settings", "FAIL", "SPYNEL_AGENT_ZERO_API_KEY absent")
    if not API_KEY:
        report("chat", "BLOCKED", "SPYNEL_AGENT_ZERO_API_KEY absent")
        report("delegation", "BLOCKED", "SPYNEL_AGENT_ZERO_API_KEY absent")
    else:
        code, data = request(
            "/api/api_message",
            {"message": "hi", "agent_profile": "spynel", "async": True},
            api=True,
        )
        ok, final = (
            poll(str(data.get("context_id")), include_logs=True)
            if code == 200 and data.get("context_id")
            else (False, data)
        )
        diagnostic = json.dumps(final).lower()
        unexpected = any(
            marker in diagnostic
            for marker in ("memorize memories extension error", "rfc error", "chpasswd")
        )
        report(
            "chat", "PASS" if ok and final.get("result") and not unexpected else "FAIL"
        )
        report(
            "memory extension",
            "PASS" if not unexpected else "FAIL",
            "no unexpected memory/RFC/chpasswd diagnostics",
        )
        code, unknown = request(
            "/api/api_message",
            {
                "message": "inspect this",
                "agent_profile": "definitely-not-real",
                "async": True,
            },
            api=True,
        )
        report(
            "unknown profile safety",
            "PASS" if code == 404 and not unknown.get("context_id") else "FAIL",
        )
        code, delegated = request(
            "/api/plugins/_goal/delegate",
            {
                "objective": "Inspect runtime mode and return a read-only summary.",
                "agent_profile": "reviewer",
                "success_criteria": ["A read-only runtime summary is returned."],
                "idempotency_key": str(uuid.uuid4()),
                "idempotency_scope": "hf-smoke",
            },
            api=True,
        )
        if code == 200 and delegated.get("context_id") and delegated.get("goal_id"):
            ok, final = poll(str(delegated["context_id"]))
            if ok and final.get("result"):
                report("delegation", "PASS", "goal executed to completion")
            elif final.get("requires_attention") or final.get("status") in {
                "blocked",
                "interrupted",
                "partially_verified",
            }:
                report(
                    "delegation",
                    "BLOCKED",
                    "worker returned an explicit attention state",
                )
            else:
                report(
                    "delegation",
                    "FAIL",
                    "goal did not complete within the finite timeout",
                )
        else:
            report("delegation", "FAIL", "goal creation failed")
        discover()
    code, _ = request("/api/agent_profile_create", {})
    report("profile-create protection", "PASS" if code in {302, 401, 403} else "FAIL")
    if not API_KEY:
        for label in ("specialist profiles", "Spynel", "Paperclip skill"):
            report(label, "BLOCKED", "SPYNEL_AGENT_ZERO_API_KEY absent")
    mandatory = {
        "health",
        "settings",
        "runtime",
        "non-root",
        "root password capability",
        "API key",
        "compatible provider",
        "chat",
        "memory extension",
        "delegation",
        "unknown profile safety",
        "profile-create protection",
        "specialist profiles",
        "Spynel",
        "Paperclip skill",
    }
    if mode == "full":
        mandatory.add("settings persistence")
    return (
        1 if any(state != "PASS" for name, state in results if name in mandatory) else 0
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("basic", "authenticated", "full"), default="full"
    )
    parser.add_argument("--basic", action="store_true")
    parser.add_argument("--authenticated", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    selected = (
        "basic" if args.basic else "authenticated" if args.authenticated else "full"
    )
    raise SystemExit(
        main(
            selected if any((args.basic, args.authenticated, args.full)) else args.mode
        )
    )
