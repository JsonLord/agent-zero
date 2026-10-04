import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.embeddings'] = MagicMock()
sys.modules['langchain.embeddings.base'] = MagicMock()
sys.modules['models'] = MagicMock()

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

def test_hf_production_runtime_mode(monkeypatch):
    monkeypatch.setenv("HF_SPACE", "true")

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
