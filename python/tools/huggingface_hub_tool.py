from python.helpers.tool import Tool, Response
from huggingface_hub import HfApi
import json

class HuggingFaceHubTool(Tool):
    """
    A tool for interacting with the Hugging Face Hub API.
    This tool is a wrapper around the huggingface_hub.HfApi client.
    """

    async def execute(self, method_name: str, method_args: dict, **kwargs) -> Response:
        """
        Dynamically calls a method on the huggingface_hub.HfApi client.

        Args:
            method_name (str): The name of the HfApi method to call (e.g., 'create_repo', 'upload_file').
            method_args (dict): A dictionary of arguments to pass to the method.
        """
        try:
            api = HfApi()

            # Check if the method exists on the HfApi client
            if not hasattr(api, method_name):
                return Response(message=f"Error: Method '{method_name}' not found on HfApi client.", break_loop=False)

            method_to_call = getattr(api, method_name)

            # Call the method with the provided arguments
            result = method_to_call(**method_args)

            # Serialize the result to a JSON string if it's not a simple type
            if isinstance(result, (str, int, float, bool, type(None))):
                response_message = str(result)
            else:
                try:
                    # Use a default function for objects that are not directly serializable
                    response_message = json.dumps(result, indent=2, default=str)
                except TypeError:
                    response_message = str(result)

            return Response(message=response_message, break_loop=False)

        except Exception as e:
            # Catch potential exceptions from the API call, like authentication errors or invalid arguments
            return Response(message=f"An error occurred while calling '{method_name}': {str(e)}", break_loop=False)
