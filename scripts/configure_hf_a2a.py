#!/usr/bin/env python3
"""Deployment-only bootstrap; does not import settings or generate credentials."""
import argparse
import json
import os
import tempfile
from pathlib import Path


def configure(application_root: Path) -> Path:
    target = application_root.resolve() / 'usr' / 'settings.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    # Invalid JSON is an operator error. Never discard existing settings silently.
    current = json.loads(target.read_text()) if target.exists() else {}
    if not isinstance(current, dict):
        raise TypeError('Settings must be a JSON object')
    current['a2a_server_enabled'] = True
    # Generated credentials belong to the existing runtime authority, never this file.
    current.pop('mcp_server_token', None)
    descriptor, temporary = tempfile.mkstemp(prefix='.settings-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w') as output:
            json.dump(current, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, default=Path(__file__).resolve().parents[1])
    configure(parser.parse_args().app_root)
