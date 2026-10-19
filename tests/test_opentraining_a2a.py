"""Pinned real ASGI/schema/broker/storage/worker boundary; no network or model calls."""
import asyncio
import contextlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.routing import Mount

from helpers import opentraining_discovery as discovery
from scripts.configure_hf_a2a import configure

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def boundary(monkeypatch):
    cfg = {'a2a_server_enabled': True, 'mcp_server_token': 'local-test-only-token'}
    counters = {'created': 0, 'removed': 0, 'initialized': 0}
    monkeypatch.setenv('A0_PUBLIC_URL', 'https://leon4gr45-opentraining.hf.space/')
    settings = types.ModuleType('helpers.settings')
    settings.get_settings = lambda: dict(cfg)
    projects = types.ModuleType('helpers.projects')
    projects.activate_project = lambda *_: None
    agent = types.ModuleType('agent')

    class Context:
        def __init__(self, *_args, **_kwargs):
            counters['created'] += 1
            self.id = str(counters['created'])
            self.log = types.SimpleNamespace(log=lambda **_: None)

        def communicate(self, message):
            async def result():
                await asyncio.sleep(0)  # Exercise overlapping requests, without provider calls.
                return 'echo:' + message.message
            return types.SimpleNamespace(result=result)

        def reset(self):
            pass

        @staticmethod
        def remove(_id):
            counters['removed'] += 1

    agent.AgentContext = Context
    agent.AgentContextType = types.SimpleNamespace(BACKGROUND='background')
    agent.UserMessage = lambda **kw: types.SimpleNamespace(**kw)
    initialize = types.ModuleType('initialize')

    def initialize_agent():
        counters['initialized'] += 1
        return {}

    initialize.initialize_agent = initialize_agent
    persist = types.ModuleType('helpers.persist_chat')
    persist.remove_chat = lambda *_: None
    import helpers
    for name, module in [('helpers.settings', settings), ('helpers.projects', projects),
                         ('agent', agent), ('initialize', initialize), ('helpers.persist_chat', persist)]:
        monkeypatch.setitem(sys.modules, name, module)
        if name.startswith('helpers.'):
            monkeypatch.setattr(helpers, name.split('.')[1], module, raising=False)
    spec = importlib.util.spec_from_file_location('opentraining_boundary_under_test', ROOT / 'helpers/fasta2a_server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, cfg, counters


@contextlib.asynccontextmanager
async def client_for(boundary):
    module, cfg, counters = boundary
    proxy = module.DynamicA2AProxy()
    app = Starlette(routes=[*discovery.discovery_routes(), Mount('/a2a', app=proxy)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        try:
            yield client, proxy, cfg, counters
        finally:
            await proxy._async_shutdown()
            proxy._startup_done = False


def payload(index=1):
    return {'jsonrpc': '2.0', 'id': str(index), 'method': 'message/send', 'params': {
        'configuration': {'acceptedOutputModes': ['application/json'], 'historyLength': 10},
        'message': {'kind': 'message', 'role': 'user', 'messageId': f'm-{index}',
                    'parts': [{'kind': 'text', 'text': f'harmless\n{index}'}]}}}


def headers(cfg):
    return {'Authorization': 'Bearer ' + cfg['mcp_server_token']}


async def complete(client, cfg, index):
    response = await client.post('/a2a/', headers=headers(cfg), json=payload(index))
    assert response.status_code == 200, response.text
    task = response.json()['result']
    assert task['status']['state'] in ('submitted', 'completed')
    for _ in range(100):
        response = await client.post('/a2a/', headers=headers(cfg), json={
            'jsonrpc': '2.0', 'id': f'get-{index}', 'method': 'tasks/get',
            'params': {'id': task['id'], 'historyLength': 10}})
        assert response.status_code == 200
        result = response.json()['result']
        assert result['id'] == task['id']
        if result['status']['state'] == 'completed':
            assert result['history'][-1]['parts'][0]['text'] == f'echo:harmless\n{index}'
            assert 'messageId' in result['history'][-1]
            return result['id']
        await asyncio.sleep(0)
    pytest.fail('Task did not complete within bounded polling')


@pytest.mark.asyncio
async def test_real_card_aliases_auth_and_serialization(boundary):
    async with client_for(boundary) as (client, proxy, cfg, calls):
        assert not proxy._startup_done
        for request_headers in ({}, {'X-API-KEY': 'incorrect'}):
            response = await client.get('/a2a/.well-known/agent.json', headers=request_headers)
            assert response.status_code == 401
        assert not proxy._startup_done
        for auth in (headers(cfg), {'X-API-KEY': cfg['mcp_server_token']}):
            first = await client.get('/a2a/.well-known/agent.json', headers=auth)
            second = await client.get('/a2a/.well-known/agent-card.json', headers=auth)
            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()
            card = first.json()
            assert card['url'] == 'https://leon4gr45-opentraining.hf.space/a2a/'
            assert card['documentationUrl'].endswith('/docs')
            assert card['capabilities']['streaming'] is False
            assert [s['id'] for s in card['skills']] == ['general_assistance']
            for skill in card['skills']:
                assert {'id', 'name', 'description', 'tags', 'examples', 'inputModes', 'outputModes'} <= skill.keys()
                assert 'input_modes' not in skill
        assert (await client.get('/a2a/docs', headers=headers(cfg))).status_code == 200
        assert calls['created'] == 0


@pytest.mark.asyncio
async def test_disabled_and_empty_authority_fail_closed(boundary):
    async with client_for(boundary) as (client, proxy, cfg, calls):
        cfg['a2a_server_enabled'] = False
        assert (await client.post('/a2a/', json=payload())).status_code == 403
        cfg['a2a_server_enabled'] = True
        for token in ('', None, ' '):
            cfg['mcp_server_token'] = token
            for path in ('/a2a/', '/a2a/t-local-test-only-token/'):
                assert (await client.post(path, json=payload())).status_code == 503
        assert not proxy._startup_done
        assert calls['created'] == 0


@pytest.mark.asyncio
async def test_real_rpc_lifecycle_and_legacy_path(boundary):
    async with client_for(boundary) as (client, _proxy, cfg, _calls):
        await complete(client, cfg, 1)
        response = await client.post('/a2a/t-local-test-only-token/', json=payload('legacy'))
        assert response.status_code == 200
        for path in ('/a2a/message/send', '/a2a/tasks/get', '/a2a/agent-card'):
            response = await client.post(path, headers=headers(cfg), json=payload())
            assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('bad', [
    {'configuration': {'accepted_output_modes': ['application/json']}, 'message': {'message_id': 'bad'}},
    {'message': {'role': 'user', 'kind': 'message', 'message_id': 'bad',
                 'parts': [{'kind': 'text', 'text': 'bad'}]}}
])
async def test_invalid_schema_is_bounded_400(boundary, bad):
    async with client_for(boundary) as (client, _proxy, cfg, calls):
        response = await client.post('/a2a/', headers=headers(cfg), json={
            'jsonrpc': '2.0', 'id': 'bad', 'method': 'message/send', 'params': bad})
        assert response.status_code == 400
        assert response.json() == {'jsonrpc': '2.0', 'id': None, 'error': {
            'code': -32600, 'message': 'Request payload validation error'}}
        assert calls['created'] == 0


@pytest.mark.asyncio
async def test_bounded_concurrent_lifecycles_and_auth_pressure(boundary):
    async with client_for(boundary) as (client, proxy, cfg, calls):
        # A synchronized cold start exercises lifecycle creation as well as task isolation.
        ids = await asyncio.wait_for(asyncio.gather(*(complete(client, cfg, n) for n in range(64))), 15)
        assert len(set(ids)) == 64
        assert calls == {'created': 64, 'removed': 64, 'initialized': 64}
        responses = await asyncio.gather(*(
            client.post('/a2a/', headers={'X-API-KEY': 'incorrect'}, json=payload(n)) for n in range(64)))
        assert all(r.status_code == 401 for r in responses)
        assert calls['created'] == 64
        assert proxy._worker_bg_task and not proxy._worker_bg_task.done()


@pytest.mark.asyncio
async def test_public_discovery(boundary):
    async with client_for(boundary) as (client, proxy, cfg, calls):
        for path in ('/health', '/docs', '/docs/a2a.json', '/api-docs'):
            response = await client.get(path)
            assert response.status_code == 200
            assert cfg['mcp_server_token'] not in response.text
        health = (await client.get('/health')).json()
        assert health['service'] == 'opentraining'
        assert health['a2a']['contract'] == '/docs/a2a.json'
        text = (await client.get('/docs')).text
        for expected in ('POST /a2a/', 'messageId', 'contextId', 'historyLength', 'acceptedOutputModes',
                         '/a2a/message/send', '/a2a/tasks/get', '/a2a/agent-card'):
            assert expected in text
        assert not proxy._startup_done
        assert calls['created'] == 0


def test_bootstrap_preserves_settings_and_no_credential(tmp_path):
    configure(tmp_path)
    path = tmp_path / 'usr/settings.json'
    assert json.loads(path.read_text()) == {'a2a_server_enabled': True}
    path.write_text(json.dumps({'custom': {'x': 1}, 'mcp_server_token': 'discard-test-token'}))
    configure(tmp_path)
    assert json.loads(path.read_text()) == {'custom': {'x': 1}, 'a2a_server_enabled': True}
    assert path.stat().st_mode & 0o777 == 0o600
    path.write_text('not json')
    with pytest.raises(ValueError):
        configure(tmp_path)
    assert path.read_text() == 'not json'


def test_startup_contract_and_secure_generic_default():
    settings = (ROOT / 'helpers/settings.py').read_text()
    assert 'a2a_server_enabled=get_default_value("a2a_server_enabled", False)' in settings
    assert 'mcp_server_token=create_auth_token()' in settings
    launcher = (ROOT / 'start_hf.sh').read_text()
    docker = (ROOT / 'docker/hf/initialize_hf.sh').read_text()
    assert 'scripts/configure_hf_a2a.py' in launcher and 'scripts/configure_hf_a2a.py' in docker
    assert 'OPENTRAINING_SOURCE_REF' in launcher and 'checkout --quiet --detach FETCH_HEAD' in launcher
    assert 'cp -rn' not in launcher and 'git clone' not in launcher
    assert 'ln -s "$APP_DIR/$state"' in launcher
    assert 'cp -f' not in launcher
    assert 'run_ui.py --host=0.0.0.0 --port=7860' in launcher
    assert 'leon4gr45-openoperator.hf.space' not in (ROOT / 'Dockerfile').read_text()
    for relative in ('helpers/ui_server.py', 'patches/helpers/ui_server.py'):
        assert '*discovery_routes(),' in (ROOT / relative).read_text()


@pytest.mark.parametrize('bad', ['https://user:password@example.com', 'file:///tmp/a',
                                'https://example.com/?token=bad', 'https://example.com/path',
                                'https://localhost', 'https://example.com:bad'])
def test_public_url_rejects_unsafe_identity(monkeypatch, bad):
    monkeypatch.setenv('HF_SPACE', 'true')
    monkeypatch.setenv('A0_PUBLIC_URL', bad)
    with pytest.raises(ValueError):
        discovery.public_url()


def test_hf_public_url_derivation(monkeypatch):
    monkeypatch.delenv('A0_PUBLIC_URL', raising=False)
    monkeypatch.delenv('SPACE_HOST', raising=False)
    monkeypatch.setenv('SPACE_ID', 'Leon4gr45/opentraining')
    assert discovery.public_url() == 'https://leon4gr45-opentraining.hf.space'


def test_alternative_launcher_executes_exact_checkout_preserving_state(tmp_path):
    """Execute the real launcher with local Git transport and dependency installation stubbed."""
    import os
    import shutil
    import subprocess
    source = tmp_path / 'source'
    source.mkdir()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    git('init', '-q', '-b', 'opentraining')
    git('config', 'user.name', 'Local fixture')
    git('config', 'user.email', 'fixture@example.invalid')
    (source / 'scripts').mkdir()
    shutil.copy(ROOT / 'scripts/configure_hf_a2a.py', source / 'scripts/configure_hf_a2a.py')
    (source / 'usr').mkdir()
    (source / 'usr/.gitkeep').touch()
    (source / 'requirements.txt').write_text('')
    (source / 'run_ui.py').write_text('''import json
from pathlib import Path
assert not Path('stale.py').exists()
assert Path('usr/training-master/experiment').read_text() == 'preserved'
settings = json.loads(Path('usr/settings.json').read_text())
assert settings['a2a_server_enabled'] is True and settings['unrelated'] == 1
print('fixture application ready')
''')
    git('add', '.')
    git('commit', '-qm', 'fixture source')
    sha = git('rev-parse', 'HEAD')
    app = tmp_path / 'app'
    app.mkdir()
    shutil.copy(ROOT / 'start_hf.sh', app / 'start_hf.sh')
    (app / 'stale.py').write_text('stale code must not execute')
    (app / 'usr/training-master').mkdir(parents=True)
    (app / 'usr/training-master/experiment').write_text('preserved')
    (app / 'usr/settings.json').write_text('{"unrelated": 1}')
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    real_git = shutil.which('git')
    (binaries / 'git').write_text('''#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if 'origin' in args and 'remote' in args and 'add' in args:
    args[-1] = os.environ['FIXTURE_SOURCE']
os.execv(os.environ['FIXTURE_GIT'], [os.environ['FIXTURE_GIT'], *args])
''')
    (binaries / 'uv').write_text('#!/bin/sh\nexit 0\n')
    # Match the launcher's python to this test interpreter without changing production logic.
    (binaries / 'python').symlink_to(sys.executable)
    for name in ('git', 'uv'):
        (binaries / name).chmod(0o755)
    env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ['PATH'],
               FIXTURE_SOURCE=str(source), FIXTURE_GIT=real_git,
               OPENTRAINING_SOURCE_REF=sha, TMPDIR=str(tmp_path))
    result = subprocess.run(['bash', str(app / 'start_hf.sh')], env=env,
                            capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    assert sha in result.stdout and 'fixture application ready' in result.stdout
    assert (app / 'usr/training-master/experiment').read_text() == 'preserved'
    assert (app / 'stale.py').exists()  # Original app/state never deleted.


@pytest.mark.asyncio
async def test_token_resolution_failure_is_bounded(boundary):
    async with client_for(boundary) as (client, proxy, _cfg, calls):
        module = boundary[0]
        def unavailable():
            raise RuntimeError('private credential-generation details')
        module.settings.get_settings = unavailable
        response = await client.post('/a2a/', json=payload())
        assert response.status_code == 503
        assert response.text == 'A2A authentication unavailable'
        assert not proxy._startup_done and calls['created'] == 0


@pytest.mark.asyncio
async def test_legacy_project_path_preserves_multiline_task(boundary):
    async with client_for(boundary) as (client, _proxy, _cfg, calls):
        response = await client.post('/a2a/t-local-test-only-token/p-project/', json=payload())
        assert response.status_code == 200
        assert calls['created'] == 1
        response = await client.post('/a2a/t-local-test-only-token/p-project/', json={
            'params': {'message': []}})
        assert response.status_code == 400
