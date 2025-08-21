from collections import OrderedDict
from datetime import datetime
from typing import Any
import uuid
from agent import Agent, AgentConfig, AgentContext, AgentContextType
from datetime import datetime
from python.helpers import files, history
import json
from initialize import initialize_agent
import subprocess
import threading
import os
from python.helpers.log import Log, LogItem

# --- Git as a Database ---
STATE_FILE_PATH = "memory/agent_state.json"
git_lock = threading.Lock()

LOG_SIZE = 1000


def git_setup():
    """Configure git for the agent."""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("HF_TOKEN environment variable not set. Git operations will fail.")
        return

    # Using placeholders as specified in the prompt
    repo_url = f"https://user:{hf_token}@huggingface.co/spaces/<your-username>/<your-space-name>"

    commands = [
        ['git', 'config', '--global', 'user.name', 'Agent-Zero'],
        ['git', 'config', '--global', 'user.email', 'agent@hf.space'],
        ['git', 'remote', 'set-url', 'origin', repo_url],
    ]

    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error setting up git: {e.stderr}")


def save_state_to_git(state_data: dict, commit_message: str):
    """Saves the state data to a JSON file and commits it to git."""
    with git_lock:
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)

            # Read existing data
            if os.path.exists(STATE_FILE_PATH):
                with open(STATE_FILE_PATH, 'r') as f:
                    try:
                        all_states = json.load(f)
                    except json.JSONDecodeError:
                        all_states = {}
            else:
                all_states = {}

            # Merge new data
            all_states.update(state_data)

            # Write updated data
            with open(STATE_FILE_PATH, 'w') as f:
                json.dump(all_states, f, ensure_ascii=False, indent=4, default=str)

            # Git operations
            subprocess.run(['git', 'add', STATE_FILE_PATH], check=True)
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)

        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e.stderr}")
        except Exception as e:
            print(f"An error occurred in save_state_to_git: {e}")


def save_tmp_chat(context: AgentContext):
    """Save context to the git-backed JSON file."""
    # Skip saving BACKGROUND contexts as they should be ephemeral
    if context.type == AgentContextType.BACKGROUND:
        return

    # Serialize the current context
    serialized_context = _serialize_context(context)
    state_data = {context.id: serialized_context}

    # Create a commit message
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_message = f"MEMORY: Agent recorded a new memory for chat {context.id} at {timestamp}"

    # Save to git
    save_state_to_git(state_data, commit_message)


def save_tmp_chats():
    """Save all contexts to the git-backed JSON file."""
    all_contexts_serialized = {}
    for _, context in AgentContext._contexts.items():
        # Skip BACKGROUND contexts as they should be ephemeral
        if context.type == AgentContextType.BACKGROUND:
            continue
        all_contexts_serialized[context.id] = _serialize_context(context)

    if not all_contexts_serialized:
        return

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_message = f"MEMORY: Batch save of all agent states at {timestamp}"
    save_state_to_git(all_contexts_serialized, commit_message)


def load_tmp_chats():
    """Load all contexts from the git-backed JSON file."""
    if not os.path.exists(STATE_FILE_PATH):
        return []

    try:
        with open(STATE_FILE_PATH, 'r') as f:
            all_states = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    ctxids = []
    for ctxid, data in all_states.items():
        try:
            ctx = _deserialize_context(data)
            ctxids.append(ctx.id)
        except Exception as e:
            print(f"Error loading chat {ctxid}: {e}")
    return ctxids


def load_json_chats(jsons: list[str]):
    """Load contexts from JSON strings"""
    ctxids = []
    for js in jsons:
        data = json.loads(js)
        if "id" in data:
            del data["id"]  # remove id to get new
        ctx = _deserialize_context(data)
        ctxids.append(ctx.id)
    return ctxids


def export_json_chat(context: AgentContext):
    """Export context as JSON string"""
    data = _serialize_context(context)
    js = json.dumps(data, ensure_ascii=False, default=str)
    return js


def remove_chat(ctxid):
    """Remove a chat or task context from the git-backed JSON file"""
    with git_lock:
        try:
            # Read existing data
            if os.path.exists(STATE_FILE_PATH):
                with open(STATE_FILE_PATH, 'r') as f:
                    try:
                        all_states = json.load(f)
                    except json.JSONDecodeError:
                        all_states = {}
            else:
                return # Nothing to remove

            # Remove the chat context
            if ctxid in all_states:
                del all_states[ctxid]
            else:
                return # Chat not found

            # Write updated data
            with open(STATE_FILE_PATH, 'w') as f:
                json.dump(all_states, f, ensure_ascii=False, indent=4, default=str)

            # Git operations
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_message = f"MEMORY: Agent removed chat {ctxid} at {timestamp}"
            subprocess.run(['git', 'add', STATE_FILE_PATH], check=True)
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)

        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e.stderr}")
        except Exception as e:
            print(f"An error occurred in remove_chat: {e}")


def _serialize_context(context: AgentContext):
    # serialize agents
    agents = []
    agent = context.agent0
    while agent:
        agents.append(_serialize_agent(agent))
        agent = agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)

    return {
        "id": context.id,
        "name": context.name,
        "created_at": (
            context.created_at.isoformat() if context.created_at
            else datetime.fromtimestamp(0).isoformat()
        ),
        "type": context.type.value,
        "last_message": (
            context.last_message.isoformat() if context.last_message
            else datetime.fromtimestamp(0).isoformat()
        ),
        "agents": agents,
        "streaming_agent": (
            context.streaming_agent.number if context.streaming_agent else 0
        ),
        "log": _serialize_log(context.log),
    }


def _serialize_agent(agent: Agent):
    data = {k: v for k, v in agent.data.items() if not k.startswith("_")}

    history = agent.history.serialize()

    return {
        "number": agent.number,
        "data": data,
        "history": history,
    }


def _serialize_log(log: Log):
    return {
        "guid": log.guid,
        "logs": [
            item.output() for item in log.logs[-LOG_SIZE:]
        ],  # serialize LogItem objects
        "progress": log.progress,
        "progress_no": log.progress_no,
    }


def _deserialize_context(data):
    config = initialize_agent()
    log = _deserialize_log(data.get("log", None))

    context = AgentContext(
        config=config,
        id=data.get("id", None),  # get new id
        name=data.get("name", None),
        created_at=(
            datetime.fromisoformat(
                # older chats may not have created_at - backcompat
                data.get("created_at", datetime.fromtimestamp(0).isoformat())
            )
        ),
        type=AgentContextType(data.get("type", AgentContextType.USER.value)),
        last_message=(
            datetime.fromisoformat(
                data.get("last_message", datetime.fromtimestamp(0).isoformat())
            )
        ),
        log=log,
        paused=False,
        # agent0=agent0,
        # streaming_agent=straming_agent,
    )

    agents = data.get("agents", [])
    agent0 = _deserialize_agents(agents, config, context)
    streaming_agent = agent0
    while streaming_agent and streaming_agent.number != data.get("streaming_agent", 0):
        streaming_agent = streaming_agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)

    context.agent0 = agent0
    context.streaming_agent = streaming_agent

    return context


def _deserialize_agents(
    agents: list[dict[str, Any]], config: AgentConfig, context: AgentContext
) -> Agent:
    prev: Agent | None = None
    zero: Agent | None = None

    for ag in agents:
        current = Agent(
            number=ag["number"],
            config=config,
            context=context,
        )
        current.data = ag.get("data", {})
        current.history = history.deserialize_history(
            ag.get("history", ""), agent=current
        )
        if not zero:
            zero = current

        if prev:
            prev.set_data(Agent.DATA_NAME_SUBORDINATE, current)
            current.set_data(Agent.DATA_NAME_SUPERIOR, prev)
        prev = current

    return zero or Agent(0, config, context)


# def _deserialize_history(history: list[dict[str, Any]]):
#     result = []
#     for hist in history:
#         content = hist.get("content", "")
#         msg = (
#             HumanMessage(content=content)
#             if hist.get("type") == "human"
#             else AIMessage(content=content)
#         )
#         result.append(msg)
#     return result


def _deserialize_log(data: dict[str, Any]) -> "Log":
    log = Log()
    log.guid = data.get("guid", str(uuid.uuid4()))
    log.set_initial_progress()

    # Deserialize the list of LogItem objects
    i = 0
    for item_data in data.get("logs", []):
        log.logs.append(
            LogItem(
                log=log,  # restore the log reference
                no=i,  # item_data["no"],
                type=item_data["type"],
                heading=item_data.get("heading", ""),
                content=item_data.get("content", ""),
                kvps=OrderedDict(item_data["kvps"]) if item_data["kvps"] else None,
                temp=item_data.get("temp", False),
            )
        )
        log.updates.append(i)
        i += 1

    return log


