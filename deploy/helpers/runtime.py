import argparse
import secrets
import os

parser = argparse.ArgumentParser()
args = {}
runtime_id = None

def initialize():
    global args
    if args: return
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument("--dockerized", type=bool, default=False)
    known, unknown = parser.parse_known_args()
    args = vars(known)

def get_arg(name: str): return args.get(name, None)
def is_dockerized() -> bool: return bool(get_arg("dockerized")) or os.getenv("HF_SPACE") == "true"
def get_runtime_id() -> str:
    global runtime_id
    if not runtime_id: runtime_id = secrets.token_hex(8)
    return runtime_id
def get_web_ui_port():
    if os.getenv("HF_SPACE") == "true": return 7860
    return get_arg("port") or 5000
