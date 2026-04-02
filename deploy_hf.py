import os
import sys
from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete

# Use token from environment
token = os.getenv("HF_TOKEN")
if not token:
    print("Error: HF_TOKEN not found in environment.")
    sys.exit(1)

repo_id = "Leon4gr45/openoperator"
api = HfApi(token=token)

print(f"Syncing repository {repo_id}...")
files_in_repo = api.list_repo_files(repo_id=repo_id, repo_type="space")

new_files = {
    "Dockerfile": "Dockerfile",
    "README.md": "README.md",
    "start_hf.sh": "start_hf.sh",
    "helpers/api.py": "patches/helpers/api.py",
    "helpers/runtime.py": "patches/helpers/runtime.py",
    "helpers/ui_server.py": "patches/helpers/ui_server.py",
    "api/api_docs.py": "patches/api/api_docs.py"
}

operations = []
# Delete files that are not in our new set (and not .gitattributes)
for f in files_in_repo:
    if f not in new_files.values() and f != ".gitattributes":
        operations.append(CommitOperationDelete(path_in_repo=f))

# Add our new files
for local, remote in new_files.items():
    if os.path.exists(local):
        operations.append(CommitOperationAdd(path_in_repo=remote, path_or_fileobj=local))

if operations:
    try:
        api.create_commit(
            repo_id=repo_id,
            operations=operations,
            commit_message="Finalize deployment structure and clean up legacy files",
            repo_type="space"
        )
        print("Finalized successfully.")
    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)
else:
    print("No changes to commit.")
