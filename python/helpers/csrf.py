import secrets
import hmac
import hashlib
import time

CSRF_SECRET = secrets.token_bytes(32)
TOKEN_TTL = 3600  # 1 hour validity

def generate_csrf_token():
    nonce = secrets.token_hex(16)  # 128-bit random
    timestamp = str(int(time.time()))
    data = f"{nonce}:{timestamp}"
    sig = hmac.new(CSRF_SECRET, data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"

def verify_csrf_token(token):
    try:
        data, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(CSRF_SECRET, data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        # check TTL
        nonce, timestamp = data.split(":")
        if time.time() - int(timestamp) > TOKEN_TTL:
            return False
        return True
    except Exception:
        return False
