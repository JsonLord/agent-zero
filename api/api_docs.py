import os
import threading
from typing import Any
from flask import Flask

class ApiDocs:
    def __init__(self, webapp: Flask, lock: threading.Lock) -> None:
        self.webapp = webapp
        self.lock = lock

    async def process(self, data: dict[str, Any], request: Any) -> dict[str, Any]:
        endpoints = []
        for rule in self.webapp.url_map.iter_rules():
            if rule.rule.startswith("/api/"):
                methods = ",".join(m for m in rule.methods if m not in ["OPTIONS", "HEAD"])
                endpoints.append({
                    "path": rule.rule,
                    "methods": methods,
                    "endpoint": rule.endpoint
                })

        return {
            "title": "Agent-Zero API Documentation",
            "version": "1.0.0",
            "hf_space": os.getenv("HF_SPACE") == "true",
            "endpoints": endpoints
        }
