import subprocess
import os
from python.helpers.tool_loader import register_tool

@register_tool
def paper_to_code(paper_name: str, paper_path: str, output_dir: str):
    """
    Converts a research paper to a code repository.

    Args:
        paper_name (str): The name of the paper.
        paper_path (str): The path to the research paper (PDF or JSON).
        output_dir (str): The directory where the generated code repository will be saved.

    Returns:
        str: The path to the generated code repository.
    """
    script_path = os.path.join(os.path.dirname(__file__), "../..", "scripts", "paper2code", "scripts", "run.sh")

    env = os.environ.copy()
    env["PAPER_NAME"] = paper_name
    env["PDF_PATH"] = paper_path
    env["OUTPUT_DIR"] = os.path.join(output_dir, paper_name)
    env["OUTPUT_REPO_DIR"] = os.path.join(output_dir, f"{paper_name}_repo")

    subprocess.run([script_path], env=env, check=True)

    return env["OUTPUT_REPO_DIR"]
