from python.helpers.files import VariablesPlugin
from python.helpers import files
import os

class Tools(VariablesPlugin):
    def get_variables(self, file: str, backup_dirs: list[str] | None = None) -> dict[str, any]:
        # Dynamically collect all tool instruction files
        folder = files.get_abs_path(os.path.dirname(file))
        folders = [folder]
        if backup_dirs:
            folders.extend([files.get_abs_path(d) for d in backup_dirs])

        prompt_files = files.get_unique_filenames_in_dirs(folders, "agent.system.tool.*.md")

        tools = []
        for prompt_file in prompt_files:
            tool = files.read_file(prompt_file)
            tools.append(tool)

        return {"tools": "\n\n".join(tools)}
