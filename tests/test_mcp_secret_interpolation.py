import os
import pytest
from helpers import mcp_handler


def test_resolve_header_secrets_substitutes_known_env_vars(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test_token_123")
    monkeypatch.setenv("GH_TOKEN", "gh_test_token_456")

    headers = {
        "Authorization": "Bearer ${ENV:HF_TOKEN}",
        "X-GitHub-Auth": "token ${ENV:GH_TOKEN}",
        "X-Static": "static-header",
    }

    resolved = mcp_handler.resolve_header_secrets(headers)

    assert resolved["Authorization"] == "Bearer hf_test_token_123"
    assert resolved["X-GitHub-Auth"] == "token gh_test_token_456"
    assert resolved["X-Static"] == "static-header"


def test_resolve_header_secrets_handles_missing_var(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)

    headers = {"Authorization": "Bearer ${ENV:MISSING_VAR}"}
    resolved = mcp_handler.resolve_header_secrets(headers)

    assert resolved["Authorization"] == "Bearer "


def test_resolve_header_secrets_rejects_invalid_syntax():
    headers = {
        "H1": "${ENV:../../ETC_PASSWD}",
        "H2": "${ENV:func()}",
        "H3": "$(whoami)",
    }

    resolved = mcp_handler.resolve_header_secrets(headers)

    # Invalid placeholders are not substituted
    assert resolved["H1"] == "${ENV:../../ETC_PASSWD}"
    assert resolved["H2"] == "${ENV:func()}"
    assert resolved["H3"] == "$(whoami)"
