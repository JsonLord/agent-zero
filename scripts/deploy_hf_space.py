#!/usr/bin/env python3
"""Deterministic deployment script to synchronize a green commit to Hugging Face Space."""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", default="Leon4gr45/openoperator", help="Target HF Space")
    parser.add_argument("--sha", default="", help="Expected GitHub commit SHA")
    args = parser.parse_args()

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("Error: HF_TOKEN environment variable is required to push to Hugging Face Space.", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parents[1]
    sha = args.sha.strip()
    if not sha:
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        except Exception:
            sha = "HEAD"

    print(f"Deploying commit SHA {sha} to Hugging Face Space {args.space}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot = Path(temp_dir) / "hf_snapshot"
        snapshot.mkdir(parents=True, exist_ok=True)

        tar_process = subprocess.Popen(["git", "archive", "--format=tar", sha], cwd=root, stdout=subprocess.PIPE)
        subprocess.check_call(["tar", "-xf", "-", "-C", str(snapshot)], stdin=tar_process.stdout)
        tar_process.wait()

        readme_path = snapshot / "README.md"
        content = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        metadata = """---
title: OpenOperator
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

"""
        if not content.startswith("---"):
            readme_path.write_text(metadata + content, encoding="utf-8")

        build_json = snapshot / "openoperator-build.json"
        build_json.write_text(f'{{\n  "source_sha": "{sha}"\n}}\n', encoding="utf-8")

        subprocess.check_call(["git", "init", "--initial-branch=main"], cwd=snapshot)
        subprocess.check_call(["git", "config", "user.name", "OpenOperator Deployer"], cwd=snapshot)
        subprocess.check_call(["git", "config", "user.email", "deploy@openoperator.local"], cwd=snapshot)
        subprocess.check_call(["git", "add", "--all"], cwd=snapshot)
        subprocess.check_call(["git", "commit", "-m", f"Deploy source revision {sha}"], cwd=snapshot)

        remote_url = f"https://huggingface.co/spaces/{args.space}"
        subprocess.check_call(["git", "remote", "add", "huggingface", remote_url], cwd=snapshot)
        subprocess.check_call(["git", "config", "http.extraHeader", f"Authorization: Bearer {hf_token}"], cwd=snapshot)
        print(f"Pushing snapshot to Hugging Face Space {args.space}...")
        subprocess.check_call(
            ["git", "push", "--force", "huggingface", "main:main"],
            cwd=snapshot,
        )

    print(f"Deployment push complete for {args.space} at SHA {sha}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
