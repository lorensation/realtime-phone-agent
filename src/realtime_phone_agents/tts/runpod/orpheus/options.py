from pydantic import BaseModel, Field

from realtime_phone_agents.config import settings

DEFAULT_HEADERS = {"Content-Type": "application/json"}
CUSTOM_TOKEN_PREFIX = "<custom_token_"


class OrpheusTTSOptions(BaseModel):
    """Configuration for the Orpheus RunPod endpoint."""

    api_url: str = Field(
        default_factory=lambda: settings.orpheus.api_url,
        description="Orpheus API URL",
    )
    model: str = Field(
        default_factory=lambda: settings.orpheus.model,
        description="Orpheus model identifier",
    )
    headers: dict[str, str] = Field(
        default_factory=lambda: DEFAULT_HEADERS.copy(),
        description="HTTP headers for API requests",
    )
    voice: str = Field(
        default_factory=lambda: settings.orpheus.voice,
        description="Voice identifier",
    )
    temperature: float = Field(
        default_factory=lambda: settings.orpheus.temperature,
        description="Sampling temperature",
    )
    top_p: float = Field(
        default_factory=lambda: settings.orpheus.top_p,
        description="Top-p sampling parameter",
    )
    max_tokens: int = Field(
        default_factory=lambda: settings.orpheus.max_tokens,
        description="Maximum tokens",
    )
    repetition_penalty: float = Field(
        default_factory=lambda: settings.orpheus.repetition_penalty,
        description="Repetition penalty",
    )
    sample_rate: int = Field(
        default_factory=lambda: settings.orpheus.sample_rate,
        description="PCM sample rate",
    )
    debug: bool = Field(
        default_factory=lambda: settings.orpheus.debug,
        description="Enable debug logging",
    )
