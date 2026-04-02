from datetime import timedelta
import os
import secrets
import threading
from flask import Flask, request, Response, session
from werkzeug.middleware.proxy_fix import ProxyFix
import initialize
from python.helpers import files, git, mcp_server, fasta2a_server
from python.helpers.files import get_abs_path
from python.helpers import runtime, dotenv, process
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.api import ApiHandler
from python.helpers.print_style import PrintStyle

# initialize the internal Flask server
webapp = Flask("app", static_folder=get_abs_path("./webui"), static_url_path="/")
webapp.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

# HF Space reverse proxy support
if os.getenv("HF_SPACE") == "true":
    webapp.wsgi_app = ProxyFix(webapp.wsgi_app, x_for=1, x_proto=1, x_host=1)

webapp.config.update(
    JSON_SORT_KEYS=False,
    SESSION_COOKIE_NAME="session_" + runtime.get_runtime_id(),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)
)

lock = threading.Lock()

@webapp.route("/", methods=["GET"])
async def serve_index():
    index = files.read_file("webui/index.html")
    return index

@webapp.route("/health", methods=["GET"])
async def health():
    return {"status": "ok", "service": "agent-zero"}

@webapp.route("/api-docs", methods=["GET"])
async def api_docs():
    from python.api.api_docs import ApiDocs
    handler = ApiDocs(webapp, lock)
    result = await handler.process({}, request)
    return result

def run():
    from werkzeug.serving import make_server
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from a2wsgi import ASGIMiddleware

    port = runtime.get_web_ui_port()
    host = "0.0.0.0"

    # register API handlers
    handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)
    for handler in handlers:
        name = handler.__module__.split(".")[-1]
        instance = handler(webapp, lock)
        async def handler_wrap(h=instance): return await h.handle_request(request=request)
        webapp.add_url_rule(f"/api/{name}", f"/{name}", handler_wrap, methods=handler.get_methods())

    middleware_routes = {
        "/mcp": ASGIMiddleware(app=mcp_server.DynamicMcpProxy.get_instance()),
        "/a2a": ASGIMiddleware(app=fasta2a_server.DynamicA2AProxy.get_instance()),
    }

    app = DispatcherMiddleware(webapp, middleware_routes)
    server = make_server(host=host, port=port, app=app, threaded=True)
    process.set_server(server)

    # Init tasks
    initialize.initialize_chats().result_sync()
    initialize.initialize_mcp()
    initialize.initialize_job_loop()

    PrintStyle().debug(f"Starting server at http://{host}:{port} ...")
    server.serve_forever()

if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
