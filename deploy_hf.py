import os
import sys
from huggingface_hub import HfApi, CommitOperationAdd

# Get token from environment
token = os.getenv("HF_TOKEN")
if not token:
    print("Error: HF_TOKEN not found in environment.")
    sys.exit(1)

repo_id = "Leon4gr45/openoperator"
api = HfApi(token=token)

files_map = {
    "Dockerfile": "Dockerfile",
    "README.md": "README.md",
    "start_hf.sh": "start_hf.sh",
    "helpers/api.py": "helpers/api.py",
    "helpers/runtime.py": "helpers/runtime.py",
    "helpers/settings.py": "helpers/settings.py",
    "helpers/ui_server.py": "helpers/ui_server.py",
    "api/api_docs.py": "api/api_docs.py"
}

operations = []
for local, remote in files_map.items():
    if os.path.exists(local):
        print(f"Adding {local} as {remote}...")
        operations.append(CommitOperationAdd(path_in_repo=remote, path_or_fileobj=local))
    else:
        print(f"Warning: {local} not found.")

try:
    print(f"Pushing to {repo_id}...")
    api.create_commit(
        repo_id=repo_id,
        operations=operations,
        commit_message="Clean up deployment script and remove hardcoded secrets",
        repo_type="space"
    )
    print("Deployment successful.")
except Exception as e:
    print(f"Deployment failed: {e}")
    sys.exit(1)
