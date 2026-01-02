import os
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError
from agent import Agent


async def ensure_huggingface_auth(agent: Agent) -> bool:
    """
    Ensures the environment is authenticated with Hugging Face Hub.
    Returns True if authenticated, False otherwise.
    """
    # Check for token in environment first as a quick check
    token = os.environ.get("HUGGINGFACE_API_TOKEN") or HfApi()._token
    api = HfApi(token=token)

    try:
        api.whoami()
        # If whoami succeeds, we are authenticated.
        return True
    except HfHubHTTPError as e:
        # This indicates the token is missing or invalid (e.g., 401 error)
        # Proceed to prompt the user.
        pass

    # Prompt the user for a new token
    input_tool = agent.get_tool(name="input", method=None, args={}, message="", loop_data=None)
    response = await input_tool.execute(
        message="Hugging Face token is invalid or missing. Please provide a valid token to continue:"
    )

    new_token = response.message.strip()
    if not new_token:
        agent.hist_add_warning("Hugging Face authentication cancelled.")
        return False

    # Use the CLI to login with the new token
    bash_tool = agent.get_tool(name="code_execution_tool", method=None, args={}, message="", loop_data=None)
    login_command = f"huggingface-cli login --token {new_token}"
    login_result = await bash_tool.execute(command=login_command)

    # Check if login was successful from the command output
    if "Login successful" not in login_result.message:
        agent.hist_add_warning(f"Hugging Face login failed. Please try again. Details: {login_result.message}")
        return False

    # Verify the new token works
    try:
        api_new = HfApi(token=new_token)
        api_new.whoami()
        # Manually set the environment variable for the current session, as huggingface-cli might not do it.
        os.environ['HUGGINGFACE_API_TOKEN'] = new_token
        return True
    except HfHubHTTPError:
        agent.hist_add_warning("The new Hugging Face token is also invalid.")
        return False
