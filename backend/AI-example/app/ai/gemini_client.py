import json

from app.core.config import settings


class GeminiClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        # Initialize the official Gemini SDK client here.
        # This file is intentionally a wrapper so the rest of the app does not
        # depend directly on Gemini-specific code.

    def generate_json(self, prompt: str) -> dict:
        # Replace this placeholder with the real Gemini call.
        #
        # Example shape:
        # response = self.client.models.generate_content(...)
        # text = response.text
        text = "{}"

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini returned invalid JSON") from exc
