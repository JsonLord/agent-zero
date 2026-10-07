import json
from flask import Flask
import pytest
from helpers import api, files


def test_health_endpoint_reports_sha_from_build_file(tmp_path, monkeypatch):
    build_file = tmp_path / "openoperator-build.json"
    build_file.write_text(json.dumps({"source_sha": "abc123def456"}), encoding="utf-8")

    real_get_abs_path = files.get_abs_path
    def fake_get_abs_path(*parts):
        if parts and parts[0] == "openoperator-build.json":
            return str(build_file)
        return real_get_abs_path(*parts)

    monkeypatch.setattr(files, "get_abs_path", fake_get_abs_path)
    monkeypatch.delenv("OPENOPERATOR_SOURCE_SHA", raising=False)

    app = Flask("test_health")
    api.register_api_route(app, None)

    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["sha"] == "abc123def456"


def test_health_endpoint_reports_sha_from_env(monkeypatch):
    monkeypatch.setenv("OPENOPERATOR_SOURCE_SHA", "envsha7890")

    app = Flask("test_health_env")
    api.register_api_route(app, None)

    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["sha"] == "envsha7890"
