import os
import sys
from huggingface_hub import HfApi, CommitOperationAdd

# Get token from environment
token = os.getenv("HF_TOKEN")
if not token:
    print("Error: HF_TOKEN not found.")
    sys.exit(1)

repo_id = "AUXteam/openfang"
api = HfApi(token=token)

files = [
    "Dockerfile",
    "README.md",
    "start_hf.sh",
    "run_ui.py",
    "helpers/api.py",
    "helpers/runtime.py",
    "helpers/settings.py",
    "api/api_docs.py"
]

operations = []
for f in files:
    if os.path.exists(f):
        operations.append(CommitOperationAdd(path_in_repo=f, path_or_fileobj=f))

try:
    api.create_commit(
        repo_id=repo_id,
        operations=operations,
        commit_message="Initial HF deployment setup with clone-at-runtime support",
        repo_type="space"
    )
    print("Pushed to HF.")
except Exception as e:
    print(f"Error: {e}")
