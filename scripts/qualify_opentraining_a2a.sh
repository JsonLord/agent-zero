#!/usr/bin/env bash
set -euo pipefail
# Operator-run after exact-SHA deployment. Never run with shell tracing enabled.
set +x
: "${OPENTRAINING_A2A_TOKEN:?OPENTRAINING_A2A_TOKEN is required}"
: "${OPENTRAINING_URL:=https://leon4gr45-opentraining.hf.space}"
export OPENTRAINING_URL OPENTRAINING_A2A_TOKEN
python - <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

base = os.environ['OPENTRAINING_URL'].rstrip('/')
token = os.environ['OPENTRAINING_A2A_TOKEN']
url = urlsplit(base)
if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
    sys.exit('OPENTRAINING_URL must be an HTTPS origin')

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
            raise RuntimeError('Oversized response')
        try:
            return response.code, json.loads(content)
        except ValueError:
            return response.code, None

def require(condition, name):
    if not condition:
        raise RuntimeError(name)
    print('PASS ' + name)

try:
    for path in ('/health', '/docs', '/docs/a2a.json'):
        require(request(path, credential=None)[0] == 200, path)
    path = '/a2a/.well-known/agent.json'
    require(request(path, credential=None)[0] in (401, 403), 'missing auth rejected')
    require(request(path, credential='invalid-qualification-token')[0] in (401, 403), 'wrong auth rejected')
    code, card = request(path)
    alias_code, alias = request('/a2a/.well-known/agent-card.json')
    require(code == alias_code == 200 and card == alias, 'equivalent authenticated cards')
    require(card.get('url') == base + '/a2a/', 'public card identity')
    payload = {'jsonrpc': '2.0', 'id': 'qualification-send', 'method': 'message/send', 'params': {
        'configuration': {'acceptedOutputModes': ['application/json']},
        'message': {'kind': 'message', 'role': 'user', 'messageId': 'qualification-message',
                    'parts': [{'kind': 'text', 'text': 'Reply with A2A qualification OK. Do not use tools or modify files.'}]}}}
    code, sent = request('/a2a/', payload)
    require(code == 200 and bool(sent.get('result', {}).get('id')), 'message/send accepted')
    task_id = sent['result']['id']
    for _ in range(60):
        code, result = request('/a2a/', {'jsonrpc': '2.0', 'id': 'qualification-get',
            'method': 'tasks/get', 'params': {'id': task_id, 'historyLength': 10}})
        require(code == 200 and result.get('result', {}).get('id') == task_id, 'tasks/get identity')
        state = result['result']['status']['state']
        if state in ('completed', 'failed', 'canceled'):
            require(state == 'completed', 'harmless task completed')
            break
        time.sleep(2)
    else:
        raise RuntimeError('Task deadline')
    payload['params'] = {'configuration': {'accepted_output_modes': ['application/json']},
                         'message': {'message_id': 'bad'}}
    code, invalid = request('/a2a/', payload)
    require(code == 400 and invalid == {'jsonrpc': '2.0', 'id': None, 'error': {
        'code': -32600, 'message': 'Request payload validation error'}}, 'bounded invalid-schema 400')
except Exception:
    # Authenticated response/error details may contain private provider or task data.
    sys.exit('FAIL qualification incomplete; inspect the service privately')
PY
