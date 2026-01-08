import os
from python.helpers.tool import Tool
from python.helpers import files

class KeywordPersonas(Tool):
    """
    An extension to prepend a persona prompt to the user's message based on keywords.
    """

    async def execute(self, message: str, **kwargs) -> str:
        """
        Inspects the user's message for keywords and prepends the appropriate persona prompt.
        """
        if not hasattr(self, 'agent'):
            return message

        prompts_dir = files.get_abs_path("prompts")
        if self.agent.config.profile:
            profile_prompts_dir = files.get_abs_path("agents", self.agent.config.profile, "prompts")
            if os.path.isdir(profile_prompts_dir):
                prompts_dir = profile_prompts_dir

        keyword_prompts_dir = os.path.join(prompts_dir, "keywords")

        message_lower = message.lower()

        try:
            if not os.path.isdir(keyword_prompts_dir):
                return message

            for filename in os.listdir(keyword_prompts_dir):
                if filename.endswith(".md"):
                    keyword = os.path.splitext(filename)[0]
                    if message_lower.startswith(keyword):
                        prompt_path = os.path.join(keyword_prompts_dir, filename)
                        with open(prompt_path, "r") as f:
                            persona_prompt = f.read()

                        if "{{query}}" in persona_prompt:
                            query = message[len(keyword):].strip()
                            persona_prompt = persona_prompt.replace("{{query}}", query)

                        return f"{persona_prompt}\n\n{message}"
        except FileNotFoundError:
            return message

        return message
