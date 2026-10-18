from agent import AgentContext, UserMessage
from python.helpers.api import ApiHandler, Request, Response
from python.helpers import files, dotenv
from initialize import initialize_agent
import os
import base64

class Chat(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict:
        text = input.get("message") or input.get("text") or ""
        ctxid = input.get("context")
        subagent = input.get("subagent") or input.get("profile")
        file_data = input.get("file")
        file_name = input.get("file_name", "uploaded_file")
        
        # Ensure latest environment variables are loaded
        dotenv.load_dotenv()
        
        # Automatically use BLABLADOR_API_KEY for 'other' provider if available
        blablador_key = os.getenv("BLABLADOR_API_KEY")
        if blablador_key:
            os.environ.setdefault("OTHER_API_KEY", blablador_key)
            os.environ.setdefault("API_KEY_OTHER", blablador_key)

        context = self.get_context(ctxid)
        
        # Dynamically use the latest settings for every request
        config = initialize_agent()
        
        # Robustly handle provider name if it's the label instead of ID
        if config.chat_model.provider == "Other OpenAI compatible":
            config.chat_model.provider = "other"
        if config.utility_model.provider == "Other OpenAI compatible":
            config.utility_model.provider = "other"

        # Override profile if provided via subagent parameter
        if subagent:
            config.profile = subagent
            if subagent not in config.knowledge_subdirs:
                config.knowledge_subdirs.append(subagent)
            # PAPERCLIP FIX (2026-07-01): scope long-term memory per subagent.
            # Without this, memory_subdir stayed "default" for every caller,
            # so ALL subagents (and all their contexts) shared one global
            # long-term memory vector store -- facts memorized under one
            # subagent/context leaked into every other subagent/context via
            # semantic recall, regardless of the (now-isolated) chat context.
            config.memory_subdir = subagent

        context.config = config
        
        # Apply config to all agents in the chain
        curr_agent = context.agent0
        while curr_agent:
            curr_agent.config = config
            curr_agent = curr_agent.data.get(curr_agent.DATA_NAME_SUBORDINATE)
            
        attachment_paths = []
        if file_data:
            # Sanitize file name to prevent path traversal
            file_name = os.path.basename(file_name)
            # Integrate into knowledge of file system
            knowledge_dir = files.get_abs_path("knowledge/custom")
            os.makedirs(knowledge_dir, exist_ok=True)
            save_path = os.path.join(knowledge_dir, file_name)
            
            try:
                if isinstance(file_data, str) and "," in file_data:
                    header, encoded = file_data.split(",", 1)
                    file_data = encoded
                decoded_data = base64.b64decode(file_data)
                with open(save_path, "wb") as f:
                    f.write(decoded_data)
            except Exception:
                with open(save_path, "w") as f:
                    f.write(str(file_data))
            
            attachment_paths.append(save_path)
        
        msg = UserMessage(text, attachment_paths)
        task = context.communicate(msg)
        result = await task.result()
        
        return {"message": result, "context": context.id}
