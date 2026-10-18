import sys
import os
import secrets
import hmac
import hashlib
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import AgentContext, AgentContextType, UserMessage
import initialize
from python.helpers import runtime, dotenv, files, git
from python.helpers.print_style import PrintStyle

app = FastAPI(title="Skilled-Agent API")

# CSRF Logic from run_ui.py
CSRF_SECRET = secrets.token_bytes(32)
TOKEN_TTL = 3600

def generate_csrf_token():
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    data = f"{nonce}:{timestamp}"
    sig = hmac.new(CSRF_SECRET, data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    attachments: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    chat_id: str

@app.on_event("startup")
async def startup_event():
    PrintStyle().print("Initializing Skilled-Agent API...")
    runtime.initialize()
    dotenv.load_dotenv()
    
    # Run migrations if necessary
    if hasattr(initialize, "initialize_migration"):
        initialize.initialize_migration()
    
    # Initialize chats
    init_chats = initialize.initialize_chats()
    init_chats.result_sync()

    # Initialize MCP
    initialize.initialize_mcp()
    
    # Start job loop
    initialize.initialize_job_loop()
    
    # Preload
    initialize.initialize_preload()
    
    PrintStyle().print("Skilled-Agent API started.")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    PrintStyle().print("Serving index.html")
    gitinfo = None
    try:
        gitinfo = git.get_git_info()
    except Exception as e:
        gitinfo = {"version": "unknown", "commit_time": "unknown"}
    
    index_content = files.read_file("webui/index.html")
    index_content = files.replace_placeholders_text(
        _content=index_content,
        version_no=gitinfo["version"],
        version_time=gitinfo["commit_time"]
    )

    csrf_token = generate_csrf_token()
    runtime_id = runtime.get_runtime_id()
    meta_tags = f'''<meta name="csrf-token" content="{csrf_token}">
    <meta name="runtime-id" content="{runtime_id}">'''
    index_content = index_content.replace("</head>", f"{meta_tags}</head>")
    return index_content

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    context = None
    if request.chat_id:
        context = AgentContext.get(request.chat_id)
        if not context:
            raise HTTPException(status_code=404, detail=f"Chat session {request.chat_id} not found")
    else:
        config = initialize.initialize_agent()
        context = AgentContext(config=config, type=AgentContextType.BACKGROUND)

    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        PrintStyle().print(f"Processing message for chat {context.id}...")
        task = context.communicate(
            UserMessage(
                message=request.message,
                attachments=request.attachments or []
            )
        )
        result = await task.result()
        return ChatResponse(response=result, chat_id=context.id)
    except Exception as e:
        PrintStyle().error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Mount static files
app.mount("/", StaticFiles(directory="webui"), name="static")
