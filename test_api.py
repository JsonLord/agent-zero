import requests
import base64
import json
import sys

BASE_URL = "https://leon4gr45-openoperator.hf.space"
# BASE_URL = "http://localhost:7860"

def test_health():
    print("Testing /health...")
    r = requests.get(f"{BASE_URL}/health")
    print(r.status_code, r.text)

def test_set_keys():
    print("Testing /set (keys)...")
    # Setting a dummy key for testing, replace with real one if needed
    data = {
        "api_key_other": "sk-dummy-key-from-api",
        "chat_model_provider": "other",
        "chat_model_api_base": "https://api.helmholtz-blablador.fz-juelich.de/v1",
        "chat_model_name": "alias-large"
    }
    r = requests.post(f"{BASE_URL}/set", json=data)
    print(r.status_code, r.text)

def test_chat():
    print("Testing /chat...")
    data = {
        "message": "Hello, who are you? Please reply briefly.",
        "profile": "agent0"
    }
    r = requests.post(f"{BASE_URL}/chat", json=data)
    print(r.status_code, r.text)

def test_chat_with_file():
    print("Testing /chat with file...")
    content = "This is a secret code: 12345. Remember it."
    encoded = base64.b64encode(content.encode()).decode()
    data = {
        "message": "What is the secret code from the file?",
        "file": encoded,
        "file_name": "secret.txt"
    }
    r = requests.post(f"{BASE_URL}/chat", json=data)
    print(r.status_code, r.text)

def test_stream():
    print("Testing /stream...")
    data = {
        "message": "Tell me a short joke.",
    }
    r = requests.post(f"{BASE_URL}/stream", json=data, stream=True)
    for line in r.iter_lines():
        if line:
            print(line.decode())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "health": test_health()
        elif cmd == "set": test_set_keys()
        elif cmd == "chat": test_chat()
        elif cmd == "file": test_chat_with_file()
        elif cmd == "stream": test_stream()
    else:
        test_health()
        # test_set_keys()
        # test_chat()
