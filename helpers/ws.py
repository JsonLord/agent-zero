import os
from urllib.parse import parse_qs

def validate_ws_origin(environ):
    if os.getenv("HF_SPACE") == "true":
        return True, None
    return True, None

def get_ws_auth(environ, auth):
    ws_password = os.getenv("WS_PASSWORD")
    client_password = (auth.get("password") or auth.get("pwd")) if isinstance(auth, dict) else None
    if not client_password:
        query = parse_qs(environ.get("QUERY_STRING", ""))
        client_password = query.get("pwd", [None])[0]

    if ws_password and client_password == ws_password:
        return True
    return False
