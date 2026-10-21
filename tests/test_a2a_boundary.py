"""Real OpenOperator ASGI routing/schema/worker/storage boundary; no model calls."""
import contextlib
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
import socketio
from flask import Flask
from starlette.responses import Response

from helpers import fasta2a_server as server
from helpers.blocking_a2a import BlockingTaskManager
from helpers.ui_server import UiServerRuntime
from plugins.argus_supervisor.helpers import service

URN = 'urn:openoperator:argus-supervisor:v1'


@contextlib.asynccontextmanager
async def application(monkeypatch, tmp_path, enabled=True):
    monkeypatch.setenv('ARGUS_SUPERVISOR_ENABLED', '1' if enabled else '0')
    monkeypatch.delenv('ARGUS_SUPERVISOR_BACKEND', raising=False)
    monkeypatch.setenv('ARGUS_SUPERVISOR_STATE_ROOT', str(tmp_path))
    monkeypatch.setenv('OPENTRAINING_A2A_URL', 'https://training.example.invalid/a2a')
    monkeypatch.delenv('OPENTRAINING_A2A_TOKEN', raising=False)
    monkeypatch.setenv('SPACE_ID', 'Leon4gr45/openoperator')
    monkeypatch.setenv('A0_PUBLIC_URL', 'https://leon4gr45-openoperator.hf.space')
    monkeypatch.setenv('SPYNEL_AGENT_ZERO_API_KEY', 'boundary-unit-token')
    monkeypatch.setattr(service, '_instance', None)
    monkeypatch.setattr(server.settings, 'get_settings', lambda: {
        'mcp_server_token': 'stale-token', 'a2a_server_enabled': True})
    initialize = Mock(side_effect=AssertionError('Model initialization must not run'))
    context = Mock(side_effect=AssertionError('AgentContext must not run'))
    monkeypatch.setattr(server, 'initialize_agent', initialize)
    monkeypatch.setattr(server, 'AgentContext', context)
    proxy = server.DynamicA2AProxy()
    monkeypatch.setattr(server.DynamicA2AProxy, 'get_instance', staticmethod(lambda: proxy))
    from helpers import mcp_server
    monkeypatch.setattr(mcp_server.DynamicMcpProxy, 'get_instance',
                        staticmethod(lambda: Response('not used', status_code=503)))
    runtime = UiServerRuntime(webapp=Flask('a2a-boundary'),
        socketio_server=socketio.AsyncServer(async_mode='asgi'), ws_manager=None,
        lock=threading.RLock(), settings_snapshot={})

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        yield
    monitor = SimpleNamespace(stage=lambda *_: contextlib.nullcontext(), lifespan=lambda: lifespan)
    app = runtime.build_asgi_app(monitor)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://unit') as client:
        try:
            yield client, proxy, initialize, context
        finally:
            await proxy._async_shutdown()
            proxy._startup_done = False
            initialize.assert_not_called()
            context.assert_not_called()


def auth():
    return {'X-API-KEY': 'boundary-unit-token'}


def request(operation='supervisor.health', metadata=None):
    return {'jsonrpc': '2.0', 'id': 'rpc-1', 'method': 'message/send', 'params': {
        'configuration': {'blocking': True, 'acceptedOutputModes': ['application/json']},
        'message': {'kind': 'message', 'role': 'user', 'messageId': 'msg-1',
            'extensions': [URN],
            'metadata': {URN: {'operation': operation, 'requestId': 'req-1'}} if metadata is None else metadata,
            'parts': [{'kind': 'data', 'data': {}}]}}}


def result(response):
    assert response.status_code == 200, response.text
    task = response.json()['result']
    assert task['status']['state'] == 'completed'
    message = task['history'][-1]
    assert 'messageId' in message
    return message['parts'][0]['data']


@pytest.mark.asyncio
@pytest.mark.parametrize('enabled', [False, True])
async def test_serialized_cards_ids_aliases_and_auth(monkeypatch, tmp_path, enabled):
    async with application(monkeypatch, tmp_path, enabled) as (client, proxy, *_):
        path = '/a2a/.well-known/agent.json'
        for headers in ({}, {'X-API-KEY': 'incorrect'}):
            assert (await client.get(path, headers=headers)).status_code == 401
        first = await client.get(path, headers=auth())
        second = await client.get('/a2a/.well-known/agent-card.json', headers=auth())
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        card = first.json()
        expected = ['general_assistance'] + (['argus_supervisor_health', 'argus_supervisor_status',
                                               'argus_campaign_list'] if enabled else [])
        assert [skill['id'] for skill in card['skills']] == expected
        assert len(set(expected)) == len(card['skills'])
        assert card['url'] == 'https://leon4gr45-openoperator.hf.space/a2a/'
        assert card['documentationUrl'] == 'https://leon4gr45-openoperator.hf.space/docs'
        for skill in card['skills']:
            assert {'id', 'name', 'description', 'tags', 'examples', 'inputModes', 'outputModes'} <= skill.keys()
            assert 'input_modes' not in skill and 'output_modes' not in skill
        assert isinstance(proxy.app.task_manager, BlockingTaskManager)
        bearer = {'Authorization': 'Bearer boundary-unit-token'}
        assert (await client.get(path, headers=bearer)).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['supervisor.health', 'supervisor.status', 'campaign.list'])
async def test_real_rpc_completed_without_backend_or_agent(monkeypatch, tmp_path, operation):
    async with application(monkeypatch, tmp_path) as (client, proxy, *_):
        response = await client.post('/a2a/', headers=auth(), json=request(operation))
        data = result(response)
        assert data['ok'] is True and data['operation'] == operation
        assert data['requestId'] == 'req-1' and 'request_id' not in data
        if operation == 'supervisor.health':
            assert data['enabled'] is True and data['backend_configured'] is False
        task_id = response.json()['result']['id']
        fetched = await client.post('/a2a/', headers=auth(), json={
            'jsonrpc': '2.0', 'id': 'get-1', 'method': 'tasks/get', 'params': {'id': task_id}})
        assert fetched.status_code == 200
        assert fetched.json()['result']['id'] == task_id
        assert fetched.json()['result']['status']['state'] == 'completed'


@pytest.mark.asyncio
async def test_real_schema_validation_is_bounded_400(monkeypatch, tmp_path):
    async with application(monkeypatch, tmp_path) as (client, _proxy, *_):
        bad = request()
        bad['params'] = {'configuration': {'accepted_output_modes': ['application/json']},
                         'message': {'message_id': 'bad'}}
        response = await client.post('/a2a/', headers=auth(), json=bad)
        assert response.status_code == 400
        assert response.json() == {'jsonrpc': '2.0', 'id': None, 'error': {
            'code': -32600, 'message': 'Request payload validation error'}}


@pytest.mark.asyncio
async def test_real_argus_errors_and_legacy_request_id(monkeypatch, tmp_path):
    async with application(monkeypatch, tmp_path) as (client, _proxy, *_):
        for envelope in ({}, {URN: []}, {URN: {'operation': 123}}):
            data = result(await client.post('/a2a/', headers=auth(), json=request(metadata=envelope)))
            assert data['error']['code'] == 'invalid_argus_envelope'
        for operation in ('campaign.claim', 'campaign.submit', 'campaign.intervene', 'campaign.cancel',
                          'campaign.release', 'campaign.mission', 'unknown'):
            data = result(await client.post('/a2a/', headers=auth(), json=request(operation)))
            assert data['error']['code'] == 'unsupported_argus_operation'
        data = result(await client.post('/a2a/', headers=auth(), json=request(metadata={URN: {
            'operation': 'supervisor.health', 'request_id': 'legacy'}})))
        assert data['requestId'] == 'legacy' and 'request_id' not in data
        monkeypatch.setenv('ARGUS_SUPERVISOR_ENABLED', '0')
        data = result(await client.post('/a2a/', headers=auth(), json=request()))
        assert data['error']['code'] == 'argus_supervisor_disabled'


@pytest.mark.asyncio
async def test_public_discovery_uses_actual_ui_router(monkeypatch, tmp_path):
    async with application(monkeypatch, tmp_path) as (client, _proxy, *_):
        for path in ('/health', '/docs', '/docs/a2a.json', '/api-docs'):
            response = await client.get(path)
            assert response.status_code == 200
            assert 'boundary-unit-token' not in response.text
        health = (await client.get('/health')).json()
        assert health['docs'] == '/docs' and health['a2a']['contract'] == '/docs/a2a.json'
        docs = (await client.get('/docs')).text
        for field in ('POST /a2a/', 'messageId', 'contextId', 'acceptedOutputModes', 'historyLength',
                      '/a2a/message/send', '/a2a/tasks/get', '/a2a/agent-card'):
            assert field in docs
        assert (await client.get('/docs/a2a.json')).json()['argusSupervisor']['mutationOperationsQualified'] is False


@pytest.mark.asyncio
async def test_internal_error_does_not_expose_exception(monkeypatch, tmp_path):
    async with application(monkeypatch, tmp_path) as (client, _proxy, *_):
        def fail():
            raise RuntimeError('private-secret-endpoint-details')
        monkeypatch.setattr(service, 'get', fail)
        response = await client.post('/a2a/', headers=auth(), json=request('supervisor.status'))
        assert result(response)['error']['code'] == 'argus_supervisor_unavailable'
        assert 'private-secret-endpoint-details' not in response.text


def test_hf_inventory_requires_installed_argus_profile(monkeypatch):
    from helpers import hf_space_defaults, subagents
    assert 'argus-supervisor' in hf_space_defaults.REQUIRED_PROFILES
    monkeypatch.setattr(subagents, 'get_available_agents_dict', lambda _: {
        name: {} for name in hf_space_defaults.REQUIRED_PROFILES if name != 'argus-supervisor'})
    with pytest.raises(RuntimeError, match='missing profiles.*argus-supervisor'):
        hf_space_defaults.assert_profiles_and_skills()


def test_wsgi_discovery_fallback_matches_asgi_contract(monkeypatch):
    from helpers import api
    from helpers.a2a_discovery import a2a_contract
    monkeypatch.setenv('OPENOPERATOR_SOURCE_SHA', '1' * 40)
    app = Flask('wsgi-discovery-boundary')
    api.register_api_route(app, threading.RLock())
    client = app.test_client()
    health = client.get('/health')
    assert health.status_code == 200
    assert health.get_json()['sha'] == '1' * 40
    assert health.get_json()['a2a']['contract'] == '/docs/a2a.json'
    docs = client.get('/docs')
    assert docs.status_code == 200 and b'POST /a2a/' in docs.data
    contract = client.get('/docs/a2a.json')
    assert contract.status_code == 200
    assert contract.get_json() == a2a_contract()
    assert contract.get_json()['argusSupervisor']['mutationOperationsQualified'] is False
