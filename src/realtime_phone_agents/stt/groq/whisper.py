from __future__ import annotations

from fastrtc import audio_to_bytes
from openai import OpenAI

from realtime_phone_agents.config import settings
from realtime_phone_agents.stt.base import STTModel


class WhisperGroqSTT(STTModel):
    """Speech-to-text via Groq's Whisper-compatible transcription API."""

    def __init__(self, model_name: str = settings.groq.stt_model):
        if not settings.groq.api_key:
            raise ValueError(
                "Groq API key is required for whisper-groq. "
                "Set GROQ__API_KEY in your environment."
            )
        self.model_name = model_name
        self.groq_client = OpenAI(
            api_key=settings.groq.api_key,
            base_url=settings.groq.base_url,
        )

    def stt(self, audio_data, **kwargs) -> str:
        payload = {
            "file": ("audio.wav", audio_to_bytes(audio_data)),
            "model": self.model_name,
            "response_format": "verbose_json",
        }

        if language := kwargs.get("language"):
            payload["language"] = language
        if prompt := kwargs.get("prompt"):
            payload["prompt"] = prompt

        response = self.groq_client.audio.transcriptions.create(**payload)
        return response.text
