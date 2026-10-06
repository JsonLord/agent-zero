import asyncio, importlib.util, json, sys, types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

@pytest.fixture()
def module(monkeypatch):
    fake_plugins=types.ModuleType("helpers.plugins"); fake_plugins.get_plugin_config=lambda *a,**k:{"memory_memorize_consolidation":False,"memory_memorize_replace_threshold":0}
    fake_errors=types.ModuleType("helpers.errors"); fake_errors.format_error=lambda error:str(error)
    fake_extension=types.ModuleType("helpers.extension"); fake_extension.Extension=object
    fake_dirty=types.ModuleType("helpers.dirty_json"); fake_dirty.DirtyJson=SimpleNamespace(parse_string=json.loads)
    fake_agent=types.ModuleType("agent"); fake_agent.LoopData=lambda:SimpleNamespace()
    fake_log=types.ModuleType("helpers.log"); fake_log.LogItem=object
    fake_defer=types.ModuleType("helpers.defer"); fake_defer.DeferredTask=MagicMock; fake_defer.THREAD_BACKGROUND="background"
    fake_memory=types.ModuleType("plugins._memory.helpers.memory")
    class Memory:
        Area=SimpleNamespace(FRAGMENTS=SimpleNamespace(value="fragments"))
        get=AsyncMock()
        format_docs_plain=staticmethod(lambda docs:[str(x) for x in docs])
    fake_memory.Memory=Memory
    fake_quality=types.ModuleType("plugins._memory.helpers.memory_quality"); fake_quality.filter_auto_memory_fragments=lambda items:[str(x) for x in items]
    fake_load=types.ModuleType("plugins._memory.tools.memory_load"); fake_load.DEFAULT_THRESHOLD=.7
    for name,value in {"helpers.plugins":fake_plugins,"helpers.errors":fake_errors,"helpers.extension":fake_extension,"helpers.dirty_json":fake_dirty,"agent":fake_agent,"helpers.log":fake_log,"helpers.defer":fake_defer,"plugins._memory.helpers.memory":fake_memory,"plugins._memory.helpers.memory_quality":fake_quality,"plugins._memory.tools.memory_load":fake_load}.items():monkeypatch.setitem(sys.modules,name,value)
    spec=importlib.util.spec_from_file_location("isolated_memory_extension",ROOT/"plugins/_memory/extensions/python/monologue_end/_50_memorize_fragments.py")
    loaded=importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded

class LogItem:
    def __init__(self):self.updates=[]
    def update(self,**kwargs):self.updates.append(kwargs)
    def stream(self,**kwargs):self.updates.append(kwargs)

def test_memory_utility_provider_failure_remains_visible(module):
    warnings=[]; module.Memory.get=AsyncMock(return_value=MagicMock())
    agent=SimpleNamespace(context=SimpleNamespace(log=SimpleNamespace(log=lambda **kwargs:warnings.append(kwargs))),history=[],read_prompt=lambda *a,**k:"prompt",concat_messages=lambda history:"history",call_utility_model=AsyncMock(side_effect=RuntimeError("provider unavailable")))
    extension=object.__new__(module.MemorizeMemories); extension.agent=agent
    asyncio.run(extension.memorize(SimpleNamespace(),LogItem()))
    assert warnings[-1]["heading"]=="Memorize memories extension error" and "provider unavailable" in warnings[-1]["content"]

def test_memory_valid_utility_result_writes_fragment_without_warning(module):
    warnings=[]; db=SimpleNamespace(insert_text=AsyncMock(),delete_documents_by_query=AsyncMock(return_value=[])); module.Memory.get=AsyncMock(return_value=db)
    agent=SimpleNamespace(context=SimpleNamespace(log=SimpleNamespace(log=lambda **kwargs:warnings.append(kwargs))),history=[],read_prompt=lambda *a,**k:"prompt",concat_messages=lambda history:"history",call_utility_model=AsyncMock(return_value='["User prefers concise answers"]'))
    extension=object.__new__(module.MemorizeMemories); extension.agent=agent
    asyncio.run(extension.memorize(SimpleNamespace(),LogItem()))
    db.insert_text.assert_awaited_once(); assert warnings==[]
