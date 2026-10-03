#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlparse


def base_url() -> str:
    raw = os.getenv("PAPERCLIP_BASE_URL", "https://leon4gr45-paperclip-founder.hf.space").rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("PAPERCLIP_BASE_URL must be a credential-free HTTPS URL")
    return raw


def safe_path(path: str) -> str:
    path = "/" + path.lstrip("/")
    parsed = urlparse(path)
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/api/")
        or ".." in unquote(parsed.path).split("/")
    ):
        raise SystemExit("Only /api/* Paperclip paths are allowed")
    return path


def request_timeout() -> float:
    try:
        timeout = float(os.getenv("PAPERCLIP_TIMEOUT", "60"))
    except ValueError as exc:
        raise SystemExit("PAPERCLIP_TIMEOUT must be a number") from exc
    if not 1 <= timeout <= 300:
        raise SystemExit("PAPERCLIP_TIMEOUT must be between 1 and 300 seconds")
    return timeout


def request(method: str, path: str, body: object | None) -> int:
    url = urljoin(base_url() + "/", safe_path(path).lstrip("/"))
    cmd = [
        "curl", "--silent", "--show-error", "--fail-with-body",
        "--proto", "=https", "--proto-redir", "=https",
        "--connect-timeout", "15", "--max-time", str(request_timeout()),
        "-H", "Accept: application/json", "-X", method.upper(), url,
    ]
    token = os.getenv("PAPERCLIP_API_TOKEN", "").strip()
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    payload = None
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        payload = json.dumps(body, ensure_ascii=False).encode()
    result = subprocess.run(cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.stdout:
        sys.stdout.buffer.write(result.stdout)
        if not result.stdout.endswith(b"\n"): print()
    if result.returncode:
        if result.stderr: sys.stderr.buffer.write(result.stderr)
        return result.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Paperclip board API helper")
    ap.add_argument("method", choices=["GET", "POST", "PATCH", "PUT", "DELETE"])
    ap.add_argument("path", help="Paperclip /api/* path")
    ap.add_argument("--json", dest="json_body", help="JSON object/array payload")
    ns = ap.parse_args()
    body = json.loads(ns.json_body) if ns.json_body is not None else None
    return request(ns.method, ns.path, body)


if __name__ == "__main__":
    raise SystemExit(main())
