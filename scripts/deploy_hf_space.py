#!/usr/bin/env python3
"""Deterministic deployment script to synchronize a green commit to Hugging Face Space."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def deployment_identity(root, requested, space):
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
        )
    )
    sha = subprocess.check_output(
        [
            "git",
            "rev-parse",
            "--verify",
            "--end-of-options",
            (requested or head) + "^{commit}",
        ],
        cwd=root,
        text=True,
    ).strip()
    print(
        f"Local HEAD: {head}\nDeployment SHA: {sha}\nWorking tree clean: {not dirty}\nTarget HF Space: {space}"
    )
    if dirty:
        raise RuntimeError(
            "Refusing deployment: working tree contains uncommitted changes. "
            "The HF deployment is built from a committed Git SHA. "
            "Commit/stash your changes before deploying."
        )
    if sha != head:
        print(
            "Explicit historical snapshot selected; local HEAD is not being deployed."
        )
    return sha


def archive_snapshot(root, sha, snapshot):
    with tempfile.TemporaryFile() as archive:
        subprocess.run(
            ["git", "archive", "--format=tar", sha],
            cwd=root,
            stdout=archive,
            check=True,
        )
        archive.seek(0)
        subprocess.run(
            ["tar", "-xf", "-", "-C", str(snapshot)], stdin=archive, check=True
        )
    (snapshot / "openoperator-build.json").write_text(
        json.dumps({"source_sha": sha}) + "\n", encoding="utf-8"
    )


def verify_health(url, sha):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read(16384))
            return response.status == 200 and data.get("sha") == sha
    except (OSError, ValueError, AttributeError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--space", default="Leon4gr45/openoperator", help="Target HF Space"
    )
    parser.add_argument("--sha", default="", help="Expected GitHub commit SHA")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Require a live /health SHA match after pushing",
    )
    parser.add_argument(
        "--health-url", default="https://leon4gr45-openoperator.hf.space/health"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        sha = deployment_identity(root, args.sha.strip(), args.space)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(
            str(error)
            if isinstance(error, RuntimeError)
            else "Invalid committed deployment SHA",
            file=sys.stderr,
        )
        return 1

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print(
            "Error: HF_TOKEN environment variable is required to push to Hugging Face Space.",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot = Path(temp_dir) / "hf_snapshot"
        snapshot.mkdir(parents=True, exist_ok=True)

        archive_snapshot(root, sha, snapshot)

        readme_path = snapshot / "README.md"
        content = (
            readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        )
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
        build_json.write_text(json.dumps({"source_sha": sha}) + "\n", encoding="utf-8")

        # Create .gitattributes to track large binary extensions via LFS / ignore if needed
        gitattributes = snapshot / ".gitattributes"
        gitattributes.write_text(
            "*.png filter=lfs diff=lfs merge=lfs -text\n*.jpg filter=lfs diff=lfs merge=lfs -text\n*.jpeg filter=lfs diff=lfs merge=lfs -text\n*.gif filter=lfs diff=lfs merge=lfs -text\n*.webm filter=lfs diff=lfs merge=lfs -text\n*.ttf filter=lfs diff=lfs merge=lfs -text\n*.woff filter=lfs diff=lfs merge=lfs -text\n*.woff2 filter=lfs diff=lfs merge=lfs -text\n",
            encoding="utf-8",
        )

        subprocess.check_call(["git", "init", "--initial-branch=main"], cwd=snapshot)
        subprocess.check_call(
            ["git", "config", "user.name", "OpenOperator Deployer"], cwd=snapshot
        )
        subprocess.check_call(
            ["git", "config", "user.email", "deploy@openoperator.local"], cwd=snapshot
        )

        # Remove offending documentation and raw binary files (like .png, .jpg, .gif, .webm, .ttf, .woff2) from snapshot
        for pattern in ["docs/res", "plugins/_whats_new/webui/assets"]:
            path = snapshot / pattern
            if path.exists():
                import shutil

                shutil.rmtree(path, ignore_errors=True)

        for binary_file in snapshot.glob("**/*"):
            if binary_file.is_file() and binary_file.suffix in [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webm",
                ".ttf",
                ".woff",
                ".woff2",
            ]:
                try:
                    binary_file.unlink()
                except OSError:
                    print("Snapshot cleanup failed; refusing upload.", file=sys.stderr)
                    return 1

        subprocess.check_call(["git", "add", "--all"], cwd=snapshot)
        subprocess.check_call(
            ["git", "commit", "-m", f"Deploy source revision {sha}"], cwd=snapshot
        )

        remote_url = f"https://huggingface.co/spaces/{args.space}"
        subprocess.check_call(
            ["git", "remote", "add", "huggingface", remote_url], cwd=snapshot
        )
        print(f"Pushing snapshot to Hugging Face Space {args.space}...")
        askpass = Path(temp_dir) / "askpass.py"
        askpass.write_text(
            "#!/usr/bin/env python3\nimport os,sys\nprint('oauth2' if 'username' in sys.argv[1].lower() else os.environ['HF_TOKEN'])\n"
        )
        askpass.chmod(0o700)
        push_env = dict(os.environ, GIT_ASKPASS=str(askpass), GIT_TERMINAL_PROMPT="0")
        result = subprocess.run(
            ["git", "push", "--force", "huggingface", "main:main"],
            cwd=snapshot,
            env=push_env,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            print(
                "HF push failed; credential-bearing transport output withheld.",
                file=sys.stderr,
            )
            return 1

    print(
        f"Snapshot push completed for {args.space} at SHA {sha}; push alone is not deployment qualification."
    )
    print(f"Verify {args.health_url}: health SHA must equal {sha}.")
    if args.verify:
        if not verify_health(args.health_url, sha):
            print(
                "Deployment unqualified: /health SHA does not match the requested SHA.",
                file=sys.stderr,
            )
            return 2
        print(
            "Deployment qualified: live /health SHA matches requested deployment SHA."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
