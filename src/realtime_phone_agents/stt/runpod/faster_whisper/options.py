from pydantic import BaseModel, Field

from realtime_phone_agents.config import settings


class FasterWhisperSTTOptions(BaseModel):
    """Configuration for the Faster Whisper OpenAI-compatible endpoint."""

    api_url: str = Field(
        default_factory=lambda: settings.faster_whisper.api_url,
        description="Base URL for the Faster Whisper API",
    )
    model: str = Field(
        default_factory=lambda: settings.faster_whisper.model,
        description="Faster Whisper model identifier",
    )
