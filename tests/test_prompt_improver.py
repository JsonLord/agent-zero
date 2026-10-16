from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dspy_gepa.py"
PROFILE = ROOT / "agents" / "prompt-improver"


def _runner():
    spec = importlib.util.spec_from_file_location("test_dspy_gepa", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_native_profile_and_skills_declared():
    profile_yaml = (PROFILE / "agent.yaml").read_text(encoding="utf-8")
    assert "name: prompt-improver" in profile_yaml
    assert "enabled: true" in profile_yaml
    for name in ("dspy-programming", "gepa-optimization", "gepa-observability"):
        assert (PROFILE / "skills" / name / "SKILL.md").is_file()
    defaults = (ROOT / "helpers" / "hf_space_defaults.py").read_text(encoding="utf-8")
    assert '"prompt-improver"' in defaults
    smoke = (ROOT / "scripts" / "smoke_hf_openoperator.py").read_text(encoding="utf-8")
    assert '"prompt-improver"' in smoke


def test_dspy_build_isolated_from_production_runtime():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert '/opt/venv-a0/bin/python -m venv /opt/venv-dspy' in docker
    assert '/opt/venv-dspy/bin/python -m pip install' in docker
    assert 'dspy==3.4.0' in docker
    assert docker.index('dspy==3.4.0') < docker.index('ENV PIP_NO_INDEX=1')
    assert '/opt/venv-dspy/bin/python -c "import dspy' in docker


def test_datasets_have_disjoint_train_val_holdout(tmp_path):
    script = _runner()
    paths = [tmp_path / name for name in ("train.jsonl", "val.jsonl", "test.jsonl")]
    for path, question in zip(paths, ("train", "val", "test")):
        path.write_text(json.dumps({"question": question, "answer": "yes"}) + "\n", encoding="utf-8")
    train, val, test = [script.load_rows(p) for p in paths]
    script.assert_disjoint(train, val, test)
    test[0]["question"] = "train"
    with pytest.raises(ValueError, match="Dataset leakage"):
        script.assert_disjoint(train, val, test)


def test_metric_and_model_id_are_deterministic():
    script = _runner()
    assert script.dspy_model_name("my-model") == "openai/my-model"
    assert script.dspy_model_name("openai/my-model") == "openai/my-model"
    assert script.score_answer(" A B ", "a  b", "exact") == 1.0
    assert script.score_answer("yes", "not yes", "exact") == 0.0
    assert script.score_answer("yes", "it is yes", "contains") == 1.0
    assert script.score_answer("", "anything", "contains") == 0.0


def test_gepa_metric_emits_feedback_and_progress(tmp_path):
    script = _runner()
    class DummyDspy:
        @staticmethod
        def Prediction(**kwargs):
            return types.SimpleNamespace(**kwargs)
    monitor = script.MetricMonitor(DummyDspy, tmp_path, "exact")
    result = monitor(types.SimpleNamespace(answer="correct"), types.SimpleNamespace(answer="wrong"))
    assert result.score == 0
    assert "Expected:" in result.feedback
    status = script.read_json(tmp_path / "status.json")
    assert status["metric_calls"] == 1
    assert status["last_score"] == 0.0
    assert status["phase"] == "gepa"


def test_inspect_is_offline_and_marks_incomplete_runs(tmp_path, capsys):
    script = _runner()
    assert script.inspect(tmp_path) == 2
    script.update_status(tmp_path, state="running", metric_calls=3)
    assert script.inspect(tmp_path) == 2
    script.update_status(tmp_path, state="completed", validation_delta=0.2)
    assert script.inspect(tmp_path) == 0
    status = script.read_json(tmp_path / "status.json")
    assert status["validation_delta"] == 0.2


def test_preflight_reports_presence_without_exposing_key(monkeypatch, capsys):
    script = _runner()
    monkeypatch.setattr(script.importlib.metadata, "version", lambda _: "3.4.0")
    for key, value in (
        ("COMPATIBLE_API", "TOP_SECRET_DONT_PRINT"),
        ("COMPATIBLE_URL", "https://llm.example.test/v1"),
        ("COMPATIBLE_MODEL", "model-1"),
    ):
        monkeypatch.setenv(key, value)
    assert script.preflight() == 0
    out = capsys.readouterr().out
    assert "TOP_SECRET_DONT_PRINT" not in out
    assert '"status": "ready"' in out


def test_main_model_setting_prefers_compatible_api(monkeypatch):
    # Confirm source contract without requesting real credentials or an endpoint.
    defaults = (ROOT / "helpers" / "hf_space_defaults.py").read_text(encoding="utf-8")
    assert 'os.environ.get("COMPATIBLE_API"' in defaults
    assert 'os.environ.get("BLABLADOR_API_KEY"' in defaults
