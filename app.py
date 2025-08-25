import os
import gradio as gr
import spaces
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow running asyncio event loop inside another
nest_asyncio.apply()

# Set required environment variables
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TZ"] = "UTC"

# Disable Docker-specific features and SSH for code execution
os.environ["DOCKERIZED"] = "false"
os.environ["CODE_EXEC_SSH_ENABLED"] = "false"
os.environ["CODE_EXEC_DOCKER_ENABLED"] = "false"

# --- Imports from Agent Zero codebase ---
from agent import AgentConfig, AgentContext, UserMessage
from models import ModelConfig, ModelType

# --- Model Configuration ---
def get_hf_chat_model_config():
    """
    Returns a default configuration for a chat model suitable for Hugging Face Spaces.
    Users may need to adjust the model name based on the hardware of their Space.
    """
    return ModelConfig(
        type=ModelType.CHAT,
        provider="huggingface",
        name="HuggingFaceH4/zephyr-7b-beta"
    )

def get_hf_embeddings_config():
    """
    Returns a default configuration for an embeddings model.
    """
    return ModelConfig(
        type=ModelType.EMBEDDING,
        provider="huggingface",
        name="sentence-transformers/all-MiniLM-L6-v2"
    )

# --- Agent Initialization ---
# A global context is used for simplicity in this single-user Gradio interface.
agent_context = None

def init_agent_context():
    """
    Initializes a global agent context if one doesn't exist.
    """
    global agent_context
    if agent_context is None:
        print("Initializing new agent context...")
        # Note: We are explicitly disabling SSH code execution in the config.
        config = AgentConfig(
            chat_model=get_hf_chat_model_config(),
            utility_model=get_hf_chat_model_config(),
            embeddings_model=get_hf_embeddings_config(),
            browser_model=get_hf_chat_model_config(),
            mcp_servers="",
            code_exec_ssh_enabled=False,
        )
        agent_context = AgentContext(config=config)
        print("Agent context initialized.")
    return agent_context

# --- Gradio Chat Logic ---
# @spaces.GPU(duration=120) # Uncomment if using a GPU-enabled Space for faster inference
def chat_with_agent(message: str, history: list):
    """
    This function is called when a user sends a message in the Gradio chat.
    It communicates with the agent and returns the response.
    """
    context = init_agent_context()

    user_msg = UserMessage(message=message)

    # The agent's core processing loop is async. We need to run it and wait for the result.
    async def get_response():
        # _process_chain is an async method that drives the agent's response generation.
        return await context._process_chain(context.get_agent(), user_msg)

    # Run the async function to get the agent's response.
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(get_response())

    # The response from the agent is what will be displayed in the chat.
    return response

# --- Gradio UI Definition ---
def main():
    """
    Defines and launches the Gradio web interface.
    """
    interface = gr.ChatInterface(
        fn=chat_with_agent,
        title="Agent Zero",
        description="A simplified version of Agent Zero running on Hugging Face Spaces. This is a personal AI assistant that can help with various tasks.",
        theme="soft",
        examples=[
            ["Hello, who are you?"],
            ["What is the capital of France?"],
            ["Write a python function to check if a number is prime."],
        ],
    )

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,  # Default port for Hugging Face Spaces
        share=False
    )

if __name__ == "__main__":
    main()
