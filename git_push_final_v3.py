import subprocess
import os

print("Attempting git push...")
result = subprocess.run(
    ["git", "push", "origin", "main"],
    cwd="hf_repo_final_v2",
    capture_output=True,
    text=True
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
