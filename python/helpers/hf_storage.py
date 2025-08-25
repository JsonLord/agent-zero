from huggingface_hub import HfApi
import json
import tempfile
import os

class HFStorageManager:
    def __init__(self):
        self.api = HfApi()
        self.dataset_name = "agent-zero-memory"

    def save_conversation(self, conversation_id: str, data: dict):
        """Save conversation to HF dataset"""
        try:
            filename = f"conversations/{conversation_id}.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(data, f, indent=2)
                f.flush()

                self.api.upload_file(
                    path_or_fileobj=f.name,
                    path_in_repo=filename,
                    repo_id=self.dataset_name,
                    repo_type="dataset"
                )
        except Exception as e:
            print(f"Failed to save conversation: {e}")

    def load_conversation(self, conversation_id: str) -> dict:
        """Load conversation from HF dataset"""
        try:
            filename = f"conversations/{conversation_id}.json"
            file_content = self.api.hf_hub_download(
                repo_id=self.dataset_name,
                filename=filename,
                repo_type="dataset"
            )
            with open(file_content, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load conversation: {e}")
            return {}
