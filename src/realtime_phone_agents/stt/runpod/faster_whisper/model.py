from __future__ import annotations

from fastrtc import audio_to_bytes
from openai import OpenAI

from realtime_phone_agents.stt.base import STTModel
from realtime_phone_agents.stt.runpod.faster_whisper.options import (
    FasterWhisperSTTOptions,
)


def _validate_api_url(api_url: str) -> str:
    if not api_url or api_url.endswith("_HERE"):
        raise ValueError(
            "Faster Whisper API URL is required for faster-whisper. "
            "Set FASTER_WHISPER__API_URL in your environment."
        )
    return api_url.rstrip("/")


class FasterWhisperSTT(STTModel):
    """Speech-to-text using an OpenAI-compatible Faster Whisper deployment."""

    def __init__(self, options: FasterWhisperSTTOptions | None = None):
        self.options = options or FasterWhisperSTTOptions()
        base_url = _validate_api_url(self.options.api_url)
        self.client = OpenAI(api_key="", base_url=f"{base_url}/v1")

    def set_model(self, model: str) -> None:
        self.options.model = model

    def set_api_url(self, api_url: str) -> None:
        self.options.api_url = _validate_api_url(api_url)
        self.client = OpenAI(api_key="", base_url=f"{self.options.api_url}/v1")

    def stt(self, audio_data) -> str:
        response = self.client.audio.transcriptions.create(
            file=("audio.wav", audio_to_bytes(audio_data)),
            model=self.options.model,
            response_format="verbose_json",
        )
        return response.text
