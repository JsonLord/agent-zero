import importlib.util
import json
import subprocess
import threading
from pathlib import Path

import httpx
import pytest
from flask import Flask, Response

from helpers import api, cache, fasta2a_server, runtime, settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for key in (
        "SPACE_ID",
        "HF_SPACE",
        "SPYNEL_AGENT_ZERO_API_KEY",
        "A0_SET_MCP_SERVER_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(settings, "create_auth_token", lambda: "generated-local")


@pytest.mark.parametrize(
    "space,legacy,expected",
    [
        (None, None, False),
        (None, "true", False),
        ("owner/space", None, True),
        ("  ", "true", False),
    ],
)
def test_real_hf_detection(monkeypatch, space, legacy, expected):
    if space is not None:
        monkeypatch.setenv("SPACE_ID", space)
    if legacy is not None:
        monkeypatch.setenv("HF_SPACE", legacy)
    assert runtime.is_huggingface_space() is expected


@pytest.mark.parametrize(
    "env,configured,expected,source",
    [
        (
            {
                "SPYNEL_AGENT_ZERO_API_KEY": "canonical",
                "A0_SET_MCP_SERVER_TOKEN": "old",
            },
            "stored",
            "canonical",
            "deployment_secret",
        ),
        (
            {"A0_SET_MCP_SERVER_TOKEN": "persisted"},
            "stored",
            "persisted",
            "persisted_environment",
        ),
        ({}, "stored", "stored", "configured"),
        ({}, "", "generated-local", "generated_local"),
        (
            {"SPACE_ID": "owner/space", "A0_SET_MCP_SERVER_TOKEN": "old"},
            "stored",
            "",
            "missing",
        ),
        (
            {"SPACE_ID": "owner/space", "SPYNEL_AGENT_ZERO_API_KEY": "canonical"},
            "old",
            "canonical",
            "deployment_secret",
        ),
    ],
)
def test_token_authority(monkeypatch, env, configured, expected, source):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert settings.resolve_api_token_with_source(configured) == (expected, source)


def test_hf_flags_mask_and_safe_diagnostics(monkeypatch):
    monkeypatch.setenv("SPACE_ID", "owner/space")
    current = settings.normalize_settings(settings.get_default_settings())
    assert not current["mcp_server_enabled"] and not current["a2a_server_enabled"]
    assert (
        settings.external_service_diagnostics(current)["incoming_api_token_source"]
        == "missing"
    )
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "canonical-test-secret")
    current = settings.normalize_settings(current)
    assert current["mcp_server_enabled"] and current["a2a_server_enabled"]
    output = settings.convert_out(current)
    assert output["settings"]["mcp_server_token"] == "************"
    assert "canonical-test-secret" not in json.dumps(output)
    assert (
        output["additional"]["external_services"]["incoming_api_token_source"]
        == "deployment_secret"
    )


def test_real_http_dispatch_preserves_browser_and_external_security(monkeypatch):
    monkeypatch.setenv("SPACE_ID", "owner/space")
    monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "canonical-test-secret")
    monkeypatch.setattr("helpers.login.get_credentials_hash", lambda: "login-hash")
    current = settings.normalize_settings(settings.get_default_settings())
    monkeypatch.setattr(settings, "get_settings", lambda: current)
    from api.api_message import ApiMessage

    async def harmless(self, input, request):
        return {"accepted": True}

    monkeypatch.setattr(ApiMessage, "process", harmless)
    from helpers import modules

    original_loader = modules.load_classes_from_file
    monkeypatch.setattr(
        modules,
        "load_classes_from_file",
        lambda path, base: (
            [ApiMessage]
            if str(path).endswith("/api_message.py")
            else original_loader(path, base)
        ),
    )
    app = Flask("hf-auth")
    app.secret_key = "unit-only"
    app.add_url_rule("/", "serve_index", lambda: Response("index"))
    app.add_url_rule("/login", "login_handler", lambda: Response("login"))
    cache.clear(api.CACHE_AREA)
    api.register_api_route(app, threading.RLock())
    client = app.test_client()
    try:
        for path in ("settings_get", "message"):
            assert client.post("/api/" + path, json={}).status_code == 302
        for path in ("settings_probe", "api_message"):
            url = "/api/" + path
            assert (
                client.post(url, json={}, headers={"X-API-KEY": "wrong"}).status_code
                == 401
            )
            response = client.post(
                url, json={}, headers={"X-API-KEY": "canonical-test-secret"}
            )
            assert response.status_code == 200
            assert "canonical-test-secret" not in response.get_data(as_text=True)
        with client.session_transaction() as session:
            session["authentication"] = "login-hash"
            session["csrf_token"] = "csrf-test"
        assert client.post("/api/settings_get", json={}).status_code == 403
        assert (
            client.post(
                "/api/settings_get", json={}, headers={"X-CSRF-Token": "csrf-test"}
            ).status_code
            == 200
        )
        monkeypatch.delenv("SPYNEL_AGENT_ZERO_API_KEY")
        assert (
            client.post(
                "/api/settings_probe", json={}, headers={"X-API-KEY": "generated-local"}
            ).status_code
            == 503
        )
    finally:
        cache.clear(api.CACHE_AREA)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["bearer", "header", "path", "wrong", "missing"])
async def test_a2a_authentication_routes(monkeypatch, mode):
    monkeypatch.setenv("SPACE_ID", "owner/space")
    if mode != "missing":
        monkeypatch.setenv("SPYNEL_AGENT_ZERO_API_KEY", "canonical-test-secret")
    monkeypatch.setattr(
        settings,
        "get_settings",
        lambda: {"mcp_server_token": "old", "a2a_server_enabled": True},
    )
    monkeypatch.setattr(fasta2a_server, "FASTA2A_AVAILABLE", True)
    proxy = object.__new__(fasta2a_server.DynamicA2AProxy)
    proxy._startup_done = True
    proxy._reconfigure_needed = False
    proxy._lock = threading.Lock()

    async def target(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"accepted":true}'})

    proxy.app = target
    headers = (
        {"Authorization": "Bearer canonical-test-secret"}
        if mode == "bearer"
        else {"X-API-KEY": "canonical-test-secret" if mode == "header" else "wrong"}
    )
    path = (
        "/a2a/t-canonical-test-secret/.well-known/agent.json"
        if mode == "path"
        else "/a2a/.well-known/agent.json"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=proxy), base_url="https://test"
    ) as client:
        response = await client.get(path, headers=headers)
    assert response.status_code == (
        503 if mode == "missing" else 401 if mode == "wrong" else 200
    )
    assert "canonical-test-secret" not in response.text


def load_deployer():
    spec = importlib.util.spec_from_file_location(
        "hf_deployer", ROOT / "scripts/deploy_hf_space.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_snapshot_refuses_dirty_and_archives_exact_commit(tmp_path, capsys):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git("config", "user.email", "test@example.test")
    git("config", "user.name", "Test")
    (tmp_path / "README.md").write_text("first")
    git("add", ".")
    git("commit", "-qm", "first")
    first = git("rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("second")
    deploy = load_deployer()
    with pytest.raises(RuntimeError, match="uncommitted"):
        deploy.deployment_identity(tmp_path, "", "test/space")
    git("commit", "-qam", "second")
    untracked = tmp_path / "untracked.txt"
    untracked.write_text("not committed")
    with pytest.raises(RuntimeError, match="uncommitted"):
        deploy.deployment_identity(tmp_path, first, "test/space")
    untracked.unlink()
    assert deploy.deployment_identity(tmp_path, first, "test/space") == first
    assert "historical snapshot" in capsys.readouterr().out
    output = tmp_path / "snapshot"
    output.mkdir()
    deploy.archive_snapshot(tmp_path, first, output)
    assert (output / "README.md").read_text() == "first"
    assert (
        json.loads((output / "openoperator-build.json").read_text())["source_sha"]
        == first
    )


def test_connection_examples_never_use_settings_mask_as_token():
    for file in (
        "mcp/server/example.html",
        "a2a/a2a-connection.html",
        "external/api-examples.html",
    ):
        source = (ROOT / "webui/components/settings" / file).read_text()
        assert 'const token = "YOUR_SPYNEL_AGENT_ZERO_API_KEY"' in source
        assert "token = response?.settings?.mcp_server_token" not in source
        assert "t-************" not in source


@pytest.mark.asyncio
@pytest.mark.parametrize("transport", ["sse", "http"])
async def test_mcp_token_path_transport_auth(monkeypatch, transport):
    from helpers import mcp_server

    proxy = object.__new__(mcp_server.DynamicMcpProxy)
    proxy._lock = threading.Lock()
    proxy.token = "canonical-test-secret"
    called = []

    async def target(scope, receive, send):
        called.append(scope["path"])

    proxy.sse_app = proxy.http_app = target

    async def unused(*args):
        pass

    scope = {
        "type": "http",
        "path": f"/t-canonical-test-secret/{transport}",
        "headers": [],
    }
    await proxy(scope, unused, unused)
    assert len(called) == 1
    with pytest.raises(mcp_server.StarletteHTTPException) as caught:
        await proxy({**scope, "path": f"/t-wrong/{transport}"}, unused, unused)
    assert caught.value.status_code == 403 and len(called) == 1


@pytest.mark.asyncio
async def test_mcp_missing_canonical_secret_fails_closed(monkeypatch):
    from helpers import mcp_server

    monkeypatch.setenv("SPACE_ID", "owner/space")
    monkeypatch.setattr(
        settings,
        "get_settings",
        lambda: {"mcp_server_enabled": True, "mcp_server_token": "old"},
    )

    async def must_not_run(request):
        raise AssertionError("unauthorized MCP dispatch")

    with pytest.raises(mcp_server.StarletteHTTPException) as caught:
        await mcp_server.mcp_middleware(None, must_not_run)
    assert caught.value.status_code == 503


@pytest.mark.parametrize("present", [False, True])
def test_actual_entrypoint_settings_block_requires_deployment_secret(tmp_path, present):
    import os

    source = (ROOT / "docker/run/fs/exe/huggingface-entrypoint.sh").read_text()
    code = source.split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "sentinel": "preserve",
                "a2a_server_enabled": not present,
                "mcp_server_enabled": not present,
            }
        )
    )
    code = code.replace('Path("/a0/usr/settings.json")', f"Path({str(path)!r})")
    env = dict(os.environ)
    if present:
        env["SPYNEL_AGENT_ZERO_API_KEY"] = "entrypoint-test-secret"
    else:
        env.pop("SPYNEL_AGENT_ZERO_API_KEY", None)
    result = subprocess.run(
        ["python3", "-c", code], env=env, capture_output=True, text=True, check=True
    )
    state = json.loads(path.read_text())
    assert (
        state["a2a_server_enabled"] is present
        and state["mcp_server_enabled"] is present
    )
    assert state["sentinel"] == "preserve"
    assert (
        "entrypoint-test-secret" not in result.stdout + result.stderr + path.read_text()
    )
    if not present:
        assert "External integrations disabled" in result.stdout


def test_deployment_health_requires_exact_sha(monkeypatch):
    deploy = load_deployer()

    class Health:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, *args):
            return b'{"sha":"expected"}'

    monkeypatch.setattr(
        deploy.urllib.request, "urlopen", lambda *args, **kwargs: Health()
    )
    assert deploy.verify_health("https://space.example/health", "expected")
    assert not deploy.verify_health("https://space.example/health", "different")
