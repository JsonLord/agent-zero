from abc import abstractmethod
import json
import threading
import os
from typing import Union, TypedDict, Dict, Any
from flask import Request, Response, Flask, request
from python.helpers.print_style import PrintStyle
from python.helpers.errors import format_error

Input = dict
Output = Union[Dict[str, Any], Response, TypedDict]

class ApiHandler:
    def __init__(self, app: Flask, thread_lock: threading.Lock):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool: return False
    @classmethod
    def requires_api_key(cls) -> bool: return False
    @classmethod
    def requires_auth(cls) -> bool:
        return False if os.getenv("HF_SPACE") == "true" else True
    @classmethod
    def get_methods(cls) -> list[str]: return ["POST", "GET"]
    @classmethod
    def requires_csrf(cls) -> bool:
        return False if os.getenv("HF_SPACE") == "true" else cls.requires_auth()

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output: pass

    async def handle_request(self, request: Request) -> Response:
        try:
            input_data: Input = {}
            if request.is_json:
                if request.data: input_data = request.get_json()
            else:
                input_data = request.args.to_dict()
                if request.method == "POST":
                    input_data.update({"data": request.get_data(as_text=True)})

            output = await self.process(input_data, request)

            if isinstance(output, Response): return output
            return Response(response=json.dumps(output), status=200, mimetype="application/json")
        except Exception as e:
            error = format_error(e)
            PrintStyle.error(f"API error: {error}")
            return Response(response=error, status=500, mimetype="text/plain")

    def get_context(self, ctxid: str):
        from agent import AgentContext
        from initialize import initialize_agent
        with self.thread_lock:
            if not ctxid:
                first = AgentContext.first()
                if first: return first
                return AgentContext(config=initialize_agent())
            got = AgentContext.get(ctxid)
            if got: return got
            return AgentContext(config=initialize_agent(), id=ctxid)
