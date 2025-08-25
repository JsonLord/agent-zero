# Simplified authentication for HF Spaces
import os
from huggingface_hub import HfApi
import secrets

class HFSpacesAuth:
    def __init__(self):
        # Use HF_TOKEN environment variable (provided by HF Spaces)
        self.hf_token = os.getenv("HF_TOKEN")
        # Generate a single session token for the space instance
        self.session_token = os.getenv("SPACE_AUTH_TOKEN", secrets.token_hex(32))

    def validate_request(self, request):
        # For HF Spaces, use simplified token validation
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return token == self.session_token
        return False
