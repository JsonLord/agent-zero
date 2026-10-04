import json
import sys
from unittest.mock import MagicMock

sys.modules['sentence_transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['pathspec'] = MagicMock()
sys.modules['watchdog'] = MagicMock()
sys.modules['watchdog.observers'] = MagicMock()
sys.modules['helpers.call_llm'] = MagicMock()
sys.modules['helpers.persist_chat'] = MagicMock()
sys.modules['models'] = MagicMock()
sys.modules['helpers.mcp_server'] = MagicMock()

from helpers.ui_server import UiServerRuntime, UiRouteHandlers

def test_health_endpoint():
    server = UiServerRuntime.create()
    server.register_http_routes()
    server.register_transport_handlers()
    client = server.webapp.test_client()

    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get("status") == "ok"

def test_api_docs_endpoint():
    server = UiServerRuntime.create()
    server.register_http_routes()
    server.register_transport_handlers()
    client = server.webapp.test_client()

    response = client.get('/api-docs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "endpoints" in data
    assert data["title"] == "Open Operator API Documentation"

def test_api_docs_handler():
    from api.api_docs import ApiDocs
    handler = ApiDocs(app=None, thread_lock=None)
    assert handler.requires_auth() is False
    assert handler.requires_csrf() is False
    assert "GET" in handler.get_methods()

if __name__ == '__main__':
    test_health_endpoint()
    test_api_docs_endpoint()
    test_api_docs_handler()
    print("ALL TESTS PASSED SUCCESSFULLY!")
