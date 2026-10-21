#!/usr/bin/env bash
# Bounded read-only smoke after exact-SHA deployment. No raw authenticated output.
set -euo pipefail
set +x
: "${SPYNEL_AGENT_ZERO_API_KEY:?SPYNEL_AGENT_ZERO_API_KEY is required}"
: "${TARGET:=https://leon4gr45-openoperator.hf.space}"
export TARGET SPYNEL_AGENT_ZERO_API_KEY
python3 - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

base = os.environ['TARGET'].rstrip('/')
parsed = urlsplit(base)
if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
    sys.exit('TARGET must be an HTTPS origin without credentials')
token = os.environ['SPYNEL_AGENT_ZERO_API_KEY']

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

opener = urllib.request.build_opener(NoRedirect)

def request(path, payload=None, credential=token):
    headers = {'Accept': 'application/json'}
    if credential:
        headers['Authorization'] = 'Bearer ' + credential
    body = None if payload is None else json.dumps(payload).encode()
    if body:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=body, headers=headers)
    try:
        response = opener.open(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        content = response.read(1048577)
        if len(content) > 1048576:
            raise RuntimeError('oversized_response')
        try:
            return response.code, json.loads(content)
        except ValueError:
            return response.code, None

def check(condition, name):
    if not condition:
        raise RuntimeError(name)
    print('PASS ' + name)

urn = 'urn:openoperator:argus-supervisor:v1'

def payload(operation, metadata=None):
    return {'jsonrpc': '2.0', 'id': 'smoke', 'method': 'message/send', 'params': {
        'configuration': {'blocking': True, 'acceptedOutputModes': ['application/json']},
        'message': {'kind': 'message', 'role': 'user', 'messageId': 'smoke', 'extensions': [urn],
            'metadata': {urn: {'operation': operation, 'requestId': 'smoke'}} if metadata is None else metadata,
            'parts': [{'kind': 'data', 'data': {}}]}}}

def argus(operation, metadata=None):
    code, result = request('/a2a/', payload(operation, metadata))
    check(code == 200 and result['result']['status']['state'] == 'completed', 'completed read-only A2A task')
    return result['result']['history'][-1]['parts'][0]['data']

try:
    for path in ('/health', '/docs', '/docs/a2a.json', '/api-docs'):
        code, body = request(path, credential=None)
        check(code == 200, path)
        if path == '/health' and os.getenv('EXPECTED_SOURCE_SHA'):
            check(body.get('sha') == os.environ['EXPECTED_SOURCE_SHA'], 'exact source provenance')
    path = '/a2a/.well-known/agent.json'
    check(request(path, credential=None)[0] in (401, 403), 'missing auth rejected')
    check(request(path, credential='invalid-smoke-token')[0] in (401, 403), 'wrong auth rejected')
    code, card = request(path)
    alias_code, alias = request('/a2a/.well-known/agent-card.json')
    check(code == alias_code == 200 and card == alias, 'equivalent Agent Cards')
    check(card['url'] == base + '/a2a/', 'public A2A identity')
    check([s['id'] for s in card['skills']] == ['general_assistance', 'argus_supervisor_health',
          'argus_supervisor_status', 'argus_campaign_list'], 'exact read-only skill IDs')
    for operation in ('supervisor.health', 'supervisor.status', 'campaign.list'):
        check(argus(operation).get('ok') is True, operation)
    check(argus('unknown')['error']['code'] == 'unsupported_argus_operation', 'unknown operation bounded')
    check(argus(None, {})['error']['code'] == 'invalid_argus_envelope', 'malformed envelope bounded')
    bad = payload('supervisor.health')
    bad['params'] = {'configuration': {'accepted_output_modes': ['application/json']},
                     'message': {'message_id': 'invalid'}}
    code, result = request('/a2a/', bad)
    check(code == 400 and result == {'jsonrpc': '2.0', 'id': None, 'error': {
        'code': -32600, 'message': 'Request payload validation error'}}, 'bounded schema validation')
except Exception:
    sys.exit('FAIL read-only smoke incomplete; inspect service privately')
PY
