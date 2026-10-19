"""Public, credential-free OpenTraining bootstrap discovery."""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route


def public_url() -> str:
    value = os.getenv('A0_PUBLIC_URL', '').strip()
    if not value:
        host = os.getenv('SPACE_HOST', '').strip()
        space = os.getenv('SPACE_ID', '').strip()
        if host:
            value = 'https://' + host
        elif space and re.fullmatch(r'[\w-]+/[\w-]+', space):
            value = 'https://' + space.lower().replace('/', '-') + '.hf.space'
        elif os.getenv('HF_SPACE') == 'true':
            value = 'https://leon4gr45-opentraining.hf.space'
        else:
            return ''
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path.strip('/')
            or any(c.isspace() for c in value)):
        raise ValueError('A0_PUBLIC_URL must be an HTTP(S) origin without credentials')
    _ = parsed.port  # Reject malformed ports.
    if (os.getenv('SPACE_ID') or os.getenv('HF_SPACE') == 'true') and parsed.hostname in (
            'localhost', '127.0.0.1', '::1'):
        raise ValueError('Public HF URL cannot use localhost')
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), '', '', ''))


def contract() -> dict:
    return {'service': 'OpenTraining', 'a2a': {
        'basePath': '/a2a/', 'agentCard': '/a2a/.well-known/agent.json',
        'agentCardCompatibility': '/a2a/.well-known/agent-card.json',
        'rpcEndpoint': '/a2a/', 'protocolVersion': '0.2.5', 'transport': 'JSON-RPC',
        'wireCase': 'camelCase', 'methods': ['message/send', 'tasks/get', 'tasks/cancel'],
        'auth': ['Authorization: Bearer', 'X-API-KEY'], 'streaming': False}}


async def health_endpoint(request):
    result = {'status': 'ok', 'service': 'opentraining', 'docs': '/docs', 'apiDocs': '/api-docs',
              'a2a': {'base': '/a2a/', 'agentCard': '/a2a/.well-known/agent.json',
                      'contract': '/docs/a2a.json'}}
    # Only expose an actual build identity; never infer one from the branch name.
    manifest = Path(__file__).resolve().parents[1] / 'opentraining-build.json'
    try:
        sha = json.loads(manifest.read_text()).get('source_sha', '')
        if re.fullmatch(r'[0-9a-f]{40}', sha):
            result['sha'] = sha
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return JSONResponse(result)


async def contract_endpoint(request):
    return JSONResponse(contract())


async def docs_endpoint(request):
    return HTMLResponse('''<!doctype html><html lang="en"><title>OpenTraining A2A integration</title>
<h1>OpenTraining A2A integration</h1>
<p>All JSON-RPC methods use <code>POST /a2a/</code>: message/send, tasks/get, tasks/cancel.
These are method names, not HTTP paths.</p>
<p>WRONG: /a2a/message/send, /a2a/tasks/get, /a2a/agent-card.</p>
<p>Use camelCase wire fields: messageId, contextId, acceptedOutputModes, historyLength.
Snake_case message_id and accepted_output_modes are invalid.</p>
<p>Authenticate using Authorization: Bearer &lt;token&gt; or X-API-KEY: &lt;token&gt;.
The credential is OpenTraining's existing generated mcp_server_token. Header auth is preferred;
legacy /a2a/t-&lt;token&gt;/ paths are supported. Never share tokenized URLs or logs.</p>
<p>Generic installations default to A2A disabled. Dedicated HF startup enables A2A;
requests fail closed if the generated token is unavailable.</p>
<p>message/send returns a submitted task. Poll tasks/get with its id until completed,
failed, or canceled. Storage is in-memory; restart loses tasks. No streaming support or
Argus/controller mutation extension is advertised. tasks/cancel is best effort and does
not establish cancellation of model-side effects.</p>
<p><a href="/docs/a2a.json">Machine contract</a> · <a href="/api-docs">API docs</a> ·
<a href="/a2a/.well-known/agent.json">Agent card (authentication required)</a> ·
<a href="/a2a/docs">FastA2A library docs (authentication required)</a></p></html>''')


async def api_docs_endpoint(request):
    return JSONResponse({'service': 'OpenTraining', 'integrationDocs': '/docs',
                         'a2a': contract()['a2a']})


def discovery_routes():
    return [Route('/health', health_endpoint, methods=['GET']),
            Route('/docs', docs_endpoint, methods=['GET']),
            Route('/docs/a2a.json', contract_endpoint, methods=['GET']),
            Route('/api-docs', api_docs_endpoint, methods=['GET'])]
