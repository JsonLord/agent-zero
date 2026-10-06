import os
import sys
import asyncio
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.modules['sentence_transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.embeddings'] = MagicMock()
sys.modules['langchain.embeddings.base'] = MagicMock()
sys.modules['models'] = MagicMock()
sys.modules.setdefault('simpleeval', MagicMock(simple_eval=lambda value, **kwargs: value))
sys.modules.setdefault('yaml', MagicMock(safe_load=lambda value: {}, safe_dump=lambda value, **kwargs: "{}"))
sys.modules.setdefault('dotenv', MagicMock(load_dotenv=lambda *args, **kwargs: True, set_key=lambda *args, **kwargs: None))
sys.modules.setdefault('nest_asyncio', MagicMock(apply=lambda: None))
sys.modules.setdefault('helpers.rfc', MagicMock())
sys.modules.setdefault('regex', MagicMock())
sys.modules.setdefault('helpers.tokens', MagicMock(count_tokens=lambda value: len(value.split()), trim_to_tokens=lambda value, count, direction="start": " ".join(value.split()[:count])))
sys.modules.setdefault('helpers.print_style', MagicMock(PrintStyle=MagicMock()))
sys.modules.setdefault('helpers.plugins', MagicMock(get_plugin_config=lambda *args, **kwargs: {}))
sys.modules.setdefault('helpers.projects', MagicMock(get_context_project_name=lambda context: None))
sys.modules.setdefault('helpers.settings', MagicMock(get_settings_for_prompt=lambda: {"workdir_path": ""}))
class _LoopData:
    def __init__(self): self.extras_temporary = {}
sys.modules.setdefault('agent', MagicMock(Agent=object, LoopData=_LoopData))

# Mock pathspec if not installed
class MockPathSpec:
    @classmethod
    def from_lines(cls, *args, **kwargs):
        return cls()
    def match_file(self, *args, **kwargs):
        return False

mock_pathspec_mod = MagicMock()
mock_pathspec_mod.PathSpec = MockPathSpec
sys.modules['pathspec'] = mock_pathspec_mod

from helpers import runtime
from plugins._promptinclude.helpers.scanner import scan_promptinclude_files
from plugins._promptinclude.extensions.python.system_prompt import _16_promptinclude as promptinclude_extension

def test_hf_production_runtime_mode(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")

    assert runtime.is_dockerized() is True
    assert runtime.is_development() is False


def test_native_dockerized_argument_marks_production(monkeypatch):
    monkeypatch.delenv("HF_SPACE", raising=False)
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.setattr(runtime, "args", {"dockerized": "true"})
    assert runtime.is_dockerized() is True
    assert runtime.is_development() is False

def test_call_development_function_in_production(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")

    mock_rfc = MagicMock()
    mock_rfc.call_rfc.side_effect = AssertionError("RFC must not be called in production mode")
    monkeypatch.setattr(runtime, "rfc", mock_rfc)

    async def local_async_fn():
        return "async_ok"

    def local_sync_fn():
        return "sync_ok"

    res_async = asyncio.run(runtime.call_development_function(local_async_fn))
    assert res_async == "async_ok"

    res_sync = asyncio.run(runtime.call_development_function(local_sync_fn))
    assert res_sync == "sync_ok"

    mock_rfc.call_rfc.assert_not_called()


def test_sync_development_function_executes_locally_in_production(monkeypatch):
    monkeypatch.setattr(runtime, "args", {"dockerized": "true"})
    mock_rfc = MagicMock()
    monkeypatch.setattr(runtime, "rfc", mock_rfc)
    assert runtime.call_development_function_sync(lambda value: value + 1, 2) == 3
    mock_rfc.call_rfc.assert_not_called()


def test_real_development_mode_uses_rfc(monkeypatch):
    monkeypatch.setattr(runtime, "args", {"dockerized": False})
    monkeypatch.setattr(runtime, "_get_rfc_url", lambda: "http://127.0.0.1:9999")
    monkeypatch.setattr(runtime, "_get_rfc_password", lambda: "masked")
    mock_rfc = MagicMock()
    mock_rfc.call_rfc = AsyncMock(return_value="remote-result")
    monkeypatch.setattr(runtime, "rfc", mock_rfc)

    def sample(value):
        return value

    assert asyncio.run(runtime.call_development_function(sample, "input")) == "remote-result"
    assert mock_rfc.call_rfc.await_count == 1

def test_promptinclude_scans_locally_in_production(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_SPACE", "true")

    inc_file = tmp_path / "test.promptinclude.md"
    inc_file.write_text("Hello from promptinclude test")

    result = asyncio.run(runtime.call_development_function(
        scan_promptinclude_files,
        str(tmp_path),
        name_pattern="*.promptinclude.md"
    ))

    assert len(result["files"]) >= 1
    assert "Hello from promptinclude test" in result["files"][0]["content"]


def test_promptinclude_extension_never_uses_rfc_in_dockerized_production(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "args", {"dockerized": "true"})
    include = tmp_path / "rules.promptinclude.md"
    include.write_text("Preserve production mode")
    mock_rfc = MagicMock()
    mock_rfc.call_rfc.side_effect = AssertionError("RFC must not be called")
    monkeypatch.setattr(runtime, "rfc", mock_rfc)
    monkeypatch.setattr(promptinclude_extension, "get_settings_for_prompt", lambda: {"workdir_path": str(tmp_path)})
    monkeypatch.setattr(promptinclude_extension.projects, "get_context_project_name", lambda context: None)
    monkeypatch.setattr(promptinclude_extension.plugins, "get_plugin_config", lambda *args, **kwargs: {})
    fake_agent = SimpleNamespace(
        context=SimpleNamespace(),
        read_prompt=lambda name, **kwargs: kwargs.get("includes", kwargs.get("content", "")),
    )
    extension = object.__new__(promptinclude_extension.PromptInclude)
    extension.agent = fake_agent
    system_prompt = []

    asyncio.run(extension.execute(system_prompt=system_prompt))

    assert "Preserve production mode" in system_prompt[0]
    mock_rfc.call_rfc.assert_not_called()

def test_true_development_mode(monkeypatch):
    monkeypatch.delenv("HF_SPACE", raising=False)
    monkeypatch.delenv("SPACE_ID", raising=False)

    orig_args = runtime.args
    try:
        runtime.args = {"dockerized": False}
        assert runtime.is_dockerized() is False
        assert runtime.is_development() is True
    finally:
        runtime.args = orig_args
