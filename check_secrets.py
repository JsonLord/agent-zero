import os

# List of secrets that are commonly used by Agent-Zero and integrated skills
COMMON_SECRETS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "HUGGINGFACE_API_KEY",
    "GOOGLE_API_KEY",
    "SERPAPI_API_KEY",
    "SEARXNG_URL"
]

def check_secrets():
    print("=== Skilled-Agent Secret Check ===")
    missing = []
    available = []
    
    for secret in COMMON_SECRETS:
        if os.getenv(secret):
            available.append(secret)
        else:
            missing.append(secret)
            
    if available:
        print(f"INFO: Available secrets in environment: {', '.join(available)}")
    
    if missing:
        print(f"WARNING: The following secrets are NOT set: {', '.join(missing)}")
        print("Please configure them in your Hugging Face Space Settings -> Secrets if your tasks require them.")
    
    print("==================================")

if __name__ == "__main__":
    check_secrets()
