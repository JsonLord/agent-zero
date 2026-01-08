import os
import json
import shutil
import stat
import subprocess
import tempfile
from huggingface_hub import HfApi
import git
from python.helpers.tool import Tool, Response

class DeployToHfSpace(Tool):
    """
    A tool to deploy a GitHub repository to a Hugging Face Space, following a
    robust, multi-step git-based workflow.
    """

    async def execute(
        self,
        space_id: str,
        github_repo_url: str,
        secrets: str,
        app_file: str = "run_ui.py",
        port: int = 7860,
        requirements_generator_command: str = "",
        start_script_content: str = "",
        **kwargs,
    ) -> Response:
        """
        Deploys a GitHub repository to a Hugging Face Space.

        :param space_id: The ID of the Hugging Face Space (e.g., "YourUser/YourSpace").
        :param github_repo_url: The URL of the source GitHub repository to be deployed.
        :param secrets: A JSON string of a dictionary containing secrets to be set (e.g., '{"HF_TOKEN": "your_token"}').
        :param app_file: The name of the main Python application file to run. Defaults to "run_ui.py".
        :param port: The port the application should run on. Defaults to 7860, the standard for Hugging Face Spaces.
        :param requirements_generator_command: An optional command to run in the source repo to generate a requirements.txt file.
        :param start_script_content: An optional string containing the entire content for a start.sh script. If provided, this will be used instead of the default.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Setup and Authentication
            hf_api = HfApi()
            token = os.environ.get("HF_TOKEN")
            if not token:
                return Response(message="Error: HF_TOKEN environment variable not set.", break_loop=True)

            hf_api.create_repo(repo_id=space_id, repo_type="space", exist_ok=True)

            # 2. Set secrets
            try:
                secrets_dict = json.loads(secrets)
                for key, value in secrets_dict.items():
                    hf_api.add_space_secret(repo_id=space_id, key=key, value=value)
            except json.JSONDecodeError:
                return Response(message="Error: Invalid JSON format for secrets.", break_loop=True)
            except Exception as e:
                return Response(message=f"Error setting secrets: {e}", break_loop=True)

            # 3. Clone Repositories
            source_repo_path = os.path.join(temp_dir, "source_repo")
            hf_space_repo_path = os.path.join(temp_dir, "hf_space_repo")

            git.Repo.clone_from(github_repo_url, source_repo_path)

            hf_repo_url = f"https://huggingface.co/spaces/{space_id}"
            hf_repo = git.Repo.clone_from(hf_repo_url, hf_space_repo_path, env={"GIT_ASKPASS": "echo", "HUGGING_FACE_HUB_TOKEN": token})


            # 4. Requirements Generation
            if requirements_generator_command:
                try:
                    subprocess.run(
                        requirements_generator_command,
                        shell=True,
                        check=True,
                        cwd=source_repo_path,
                    )
                except subprocess.CalledProcessError as e:
                    return Response(message=f"Error generating requirements.txt: {e}", break_loop=True)

            # 5. File Copy and Initial Push
            for item in os.listdir(source_repo_path):
                s = os.path.join(source_repo_path, item)
                d = os.path.join(hf_space_repo_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

            hf_repo.git.add(A=True)
            if hf_repo.is_dirty(untracked_files=True):
                hf_repo.git.commit("-m", "Add project files")
                hf_repo.git.push()


            # 6. Scheduler Setup and Final Push
            start_script_path = os.path.join(hf_space_repo_path, "start.sh")
            if not start_script_content:
                start_script_content = f"#!/bin/bash\npython {app_file} --port {port}\n"

            with open(start_script_path, "w") as f:
                f.write(start_script_content)

            # Make the script executable
            st = os.stat(start_script_path)
            os.chmod(start_script_path, st.st_mode | stat.S_IEXEC)

            hf_repo.git.add("start.sh")
            if hf_repo.is_dirty():
                hf_repo.git.commit("-m", "Add startup script")
                hf_repo.git.push()


            return Response(message=f"Successfully deployed to Hugging Face Space: {space_id}", break_loop=False)

        except Exception as e:
            return Response(message=f"An unexpected error occurred during deployment: {e}", break_loop=True)
        finally:
            shutil.rmtree(temp_dir)
