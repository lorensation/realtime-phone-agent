from pydantic import BaseModel, Field

from realtime_phone_agents.config import settings


class MistralTTSOptions(BaseModel):
    """Configuration for the Mistral Voxtral text-to-speech provider."""

    api_key: str = Field(
        default_factory=lambda: settings.mistral.api_key,
        description="Mistral API key",
    )
    base_url: str = Field(
        default_factory=lambda: settings.mistral.base_url,
        description="Mistral base URL",
    )
    tts_model: str = Field(
        default_factory=lambda: settings.mistral.tts_model,
        description="Mistral Voxtral model identifier",
    )
    voice_id: str = Field(
        default_factory=lambda: settings.mistral.voice_id,
        description="Default multilingual voice ID",
    )
    voice_id_en: str = Field(
        default_factory=lambda: settings.mistral.voice_id_en,
        description="Optional English-specific voice ID override",
    )
    voice_id_es: str = Field(
        default_factory=lambda: settings.mistral.voice_id_es,
        description="Optional Spanish-specific voice ID override",
    )
    response_format: str = Field(
        default_factory=lambda: settings.mistral.response_format,
        description="Speech response format",
    )
    sample_rate_hz: int = Field(
        default_factory=lambda: settings.mistral.sample_rate_hz,
        description="Expected sample rate for PCM speech responses",
    )
