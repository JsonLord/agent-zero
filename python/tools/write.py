from python.helpers.tool import Tool

class Write(Tool):
    def __init__(self, agent, **kwargs):
        super().__init__(agent, **kwargs)

    async def execute(self, filepath: str, content: str, **kwargs):
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            return f"File '{filepath}' written successfully."
        except Exception as e:
            return f"Error writing to file '{filepath}': {e}"
