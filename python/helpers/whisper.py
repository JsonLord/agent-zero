import base64
import tempfile
import os
from gradio_client import Client, handle_file

# Initialize the client with the model
client = Client("Nabeelbhat/Audio_Transcribe_App")

async def transcribe(model_name: str, audio_bytes_b64: str):
    """
    Transcribes an audio file using the Nabeelbhat/Audio_Transcribe_App Gradio client.

    Args:
        model_name (str): The name of the model (not used in this implementation).
        audio_bytes_b64 (str): The base64 encoded audio data.

    Returns:
        dict: The transcription result.
    """
    try:
        audio_bytes = base64.b64decode(audio_bytes_b64)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_audio_file.write(audio_bytes)
            temp_path = temp_audio_file.name

        try:
            # Handle the file and make the prediction
            result = client.predict(
                audio_file=handle_file(temp_path),
                api_name="/predict"
            )
            return {"text": result}  # The API returns a dictionary with a "text" key
        finally:
            os.remove(temp_path)
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return None

# The following functions are no longer needed but are kept for compatibility
# to avoid breaking other parts of the application that might call them.
async def preload(model_name:str):
    pass

async def is_downloading():
    return False

async def is_downloaded():
    return True
