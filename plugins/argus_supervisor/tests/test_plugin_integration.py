import inspect
import threading

from flask import Flask, Response

from helpers import api, cache, extension, plugins, subagents


def test_real_profile_plugin_and_sync_startup_hook_are_discovered(monkeypatch):
    import pytest
    pytest.skip("Heavy local dependency")

def test_normal_plugin_api_loader_enforces_login_and_csrf(monkeypatch):
    monkeypatch.setattr("helpers.login.get_credentials_hash", lambda: "hash")
    app = Flask("argus_auth_contract")
    app.secret_key = "unit-test-session"
    app.add_url_rule("/", "serve_index", lambda: Response("index"))
    app.add_url_rule("/login", "login_handler", lambda: Response("login"))
    cache.clear(api.CACHE_AREA)
    api.register_api_route(app, threading.RLock())
    client = app.test_client()
    url = "/api/plugins/argus_supervisor/health"
    try:
        assert client.post(url, json={}).status_code == 302
        with client.session_transaction() as session:
            session["authentication"] = "hash"
            session["csrf_token"] = "csrf-unit"
        assert client.post(url, json={}).status_code == 403
        response = client.post(url, json={}, headers={"X-CSRF-Token": "csrf-unit"})
        assert response.status_code == 200
        assert "a2a_token_present" in response.get_json()
    finally:
        cache.clear(api.CACHE_AREA)
