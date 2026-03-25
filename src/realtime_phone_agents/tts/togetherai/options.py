from pydantic import BaseModel, Field

from realtime_phone_agents.config import settings

DEFAULT_VOICES = {
    "canopylabs/orpheus-3b-0.1-ft": "tara",
    "hexgrad/Kokoro-82M": "af_heart",
    "cartesia/sonic-2": "sarah",
    "cartesia/sonic": "sarah",
}


class TogetherTTSOptions(BaseModel):
    """Configuration for Together AI TTS."""

    api_key: str = Field(
        default_factory=lambda: settings.together.api_key,
        description="Together AI API key",
    )
    api_url: str = Field(
        default_factory=lambda: settings.together.api_url,
        description="Together AI API URL",
    )
    model: str = Field(
        default_factory=lambda: settings.together.model,
        description="Together AI model identifier",
    )
    voice: str = Field(
        default_factory=lambda: settings.together.voice,
        description="Voice to use",
    )
    sample_rate: int = Field(
        default_factory=lambda: settings.together.sample_rate,
        description="PCM sample rate",
    )
