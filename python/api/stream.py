from agent import AgentContext, UserMessage
from python.helpers.api import ApiHandler, Request, Response
from python.helpers import files, dotenv
from initialize import initialize_agent
import os
import json
import base64
import queue
import traceback

class Stream(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> Response:
        try:
            text = input.get("message") or input.get("text") or ""
            ctxid = input.get("context")
            subagent = input.get("subagent") or input.get("profile")
            file_data = input.get("file")
            file_name = input.get("file_name", "uploaded_file")
            
            dotenv.load_dotenv()
            
            # Automatically use BLABLADOR_API_KEY for 'other' provider if available
            blablador_key = os.getenv("BLABLADOR_API_KEY")
            if blablador_key:
                os.environ.setdefault("OTHER_API_KEY", blablador_key)
                os.environ.setdefault("API_KEY_OTHER", blablador_key)

            context = self.get_context(ctxid)
            config = initialize_agent()
            
            if config.chat_model.provider == "Other OpenAI compatible":
                config.chat_model.provider = "other"
            if config.utility_model.provider == "Other OpenAI compatible":
                config.utility_model.provider = "other"

            if subagent:
                config.profile = subagent
                if subagent not in config.knowledge_subdirs:
                    config.knowledge_subdirs.append(subagent)
                    
            context.config = config
            curr_agent = context.agent0
            while curr_agent:
                curr_agent.config = config
                curr_agent = curr_agent.data.get(curr_agent.DATA_NAME_SUBORDINATE)

            attachment_paths = []
            if file_data:
                # Sanitize file name to prevent path traversal
                file_name = os.path.basename(file_name)
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

            sync_queue = queue.Queue()
            context.stream_queue = sync_queue
            
            msg = UserMessage(text, attachment_paths)
            task = context.communicate(msg)

            def generate():
                try:
                    while task.is_alive() or not sync_queue.empty():
                        try:
                            chunk = sync_queue.get(timeout=0.1)
                            yield f"data: {json.dumps(chunk)}\n\n"
                        except queue.Empty:
                            if not task.is_alive():
                                break
                            continue
                        except Exception as e:
                            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
                            break
                    
                    try:
                        result = task.result_sync(timeout=300)
                        yield f"data: {json.dumps({'type': 'final', 'text': result})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'text': f'Result error: {str(e)}'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'text': f'Generator error: {str(e)}'})}\n\n"
                finally:
                    if hasattr(context, 'stream_queue'):
                        delattr(context, 'stream_queue')

            return Response(generate(), mimetype='text/event-stream')
        except Exception as e:
            return Response(f"Error: {str(e)}\n{traceback.format_exc()}", status=500)
