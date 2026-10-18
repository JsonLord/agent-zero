#!/usr/bin/env python3
"""
Patch Agent Zero for Hugging Face's non-root runtime.

Agent Zero's upstream prepare.py always calls settings.set_root_password(),
which ultimately executes `chpasswd`. That requires root and fails when the
Space intentionally runs as UID 1000.

We keep runtime non-root and change only set_root_password(): when EUID != 0,
it returns without invoking chpasswd. Root behavior remains unchanged.
"""

from pathlib import Path

path = Path("/a0/helpers/settings.py")
if not path.exists():
    raise SystemExit(f"Agent Zero settings file not found: {path}")

text = path.read_text(encoding="utf-8")

signature = "def set_root_password(password: str):\n"
if signature not in text:
    raise SystemExit("Could not locate set_root_password() in /a0/helpers/settings.py")

guard = (
    "def set_root_password(password: str):\n"
    "    # Hugging Face/OpenOperator runs intentionally as non-root UID 1000.\n"
    "    # Root password management is irrelevant there and `chpasswd` would fail.\n"
    "    if os.geteuid() != 0:\n"
    "        PrintStyle.info(\"Skipping root password change in non-root runtime.\")\n"
    "        return\n"
)

# Idempotent patch.
if "Skipping root password change in non-root runtime." not in text:
    text = text.replace(signature, guard, 1)
    path.write_text(text, encoding="utf-8")
    print("Patched Agent Zero set_root_password() for non-root runtime.")
else:
    print("Agent Zero non-root password patch already present.")
