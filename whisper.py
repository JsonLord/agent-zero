def load_model(*args, **kwargs):
    class MockModel:
        def transcribe(self, *args, **kwargs):
            return {"text": "Whisper is disabled in this deployment"}
    return MockModel()
