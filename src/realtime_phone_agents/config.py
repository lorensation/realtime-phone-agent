from typing import ClassVar

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# --- Groq Configuration ---
class GroqSettings(BaseModel):
    api_key: str = Field(default="", description="Groq API Key")
    base_url: str = Field(
        default="https://api.groq.com/openai/v1", description="Groq Base URL"
    )
    model: str = Field(default="openai/gpt-oss-20b", description="Groq Model to use")
    stt_model: str = Field(
        default="whisper-large-v3", description="Groq STT model to use"
    )


# --- Groq Configuration ---
class OpenAISettings(BaseModel):
    api_key: str = Field(default="", description="OpenAI API Key")
    model: str = Field(default="gpt-4o-mini", description="OpenAI Model to use")


# --- Superlinked Configuration ---
class SuperlinkedSettings(BaseModel):
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding Model to use for Superlinked",
    )
    area_min_value: int = Field(
        default=0, description="Minimum indexed room area in square meters"
    )
    area_max_value: int = Field(
        default=100, description="Maximum indexed room area in square meters"
    )
    price_min_value: int = Field(
        default=0, description="Minimum indexed orientative price in euros"
    )
    price_max_value: int = Field(
        default=1000, description="Maximum indexed orientative price in euros"
    )


# --- Knowledge Base Configuration ---
class KnowledgeBaseSettings(BaseModel):
    default_bundle_path: str = Field(
        default="data/blue_sardine_kb/2026-03-24",
        description="Default versioned knowledge bundle path to auto-ingest at startup",
    )
    auto_ingest_default_bundle: bool = Field(
        default=True,
        description="Automatically ingest the default knowledge bundle at startup",
    )


# --- Qdrant Configuration ---
class QdrantSettings(BaseModel):
    host: str = Field(default="qdrant", description="Qdrant Host")
    port: int = Field(default=6333, description="Qdrant Port")
    api_key: str = Field(default="", description="Qdrant API Key")
    use_https: bool = Field(default=False, description="Use HTTPS for Qdrant")


# --- RunPod Configuration ---
class RunPodSettings(BaseModel):
    api_key: str = Field(default="", description="RunPod API Key")
    faster_whisper_gpu_type: str = Field(
        default="NVIDIA GeForce RTX 4090", description="Faster Whisper GPU type"
    )
    orpheus_gpu_type: str = Field(
        default="NVIDIA GeForce RTX 5090", description="Orpheus GPU type"
    )
    orpheus_image_name: str = Field(
        default="theneuralmaze/orpheus-llamacpp-server:latest",
        description="Container image for Orpheus llama.cpp pods",
    )


# --- Faster Whisper STT Configuration ---
class FasterWhisperSettings(BaseModel):
    api_url: str = Field(default="", description="Faster Whisper API URL")
    model: str = Field(
        default="Systran/faster-whisper-large-v3",
        description="Faster Whisper model",
    )


# --- Orpheus TTS Configuration ---
class OrpheusTTSSettings(BaseModel):
    api_url: str = Field(default="", description="Orpheus TTS API URL")
    model: str = Field(default="orpheus-3b-0.1-ft", description="Orpheus TTS model")
    voice: str = Field(default="tara", description="Default Orpheus voice")
    temperature: float = Field(default=0.6, description="Temperature for generation")
    top_p: float = Field(default=0.9, description="Top-p sampling parameter")
    max_tokens: int = Field(default=1200, description="Maximum tokens to generate")
    repetition_penalty: float = Field(default=1.1, description="Repetition penalty")
    sample_rate: int = Field(default=24000, description="Audio sample rate")
    debug: bool = Field(default=False, description="Enable Orpheus debug mode")


# --- Spanish Orpheus TTS Configuration ---
class OrpheusSpanishTTSSettings(BaseModel):
    api_url: str = Field(default="", description="Spanish Orpheus TTS API URL")
    model: str = Field(
        default="3b-es_it-ft-research_release.q8_0.gguf",
        description="Spanish Orpheus TTS model",
    )
    voice: str = Field(default="Maria", description="Default Spanish Orpheus voice")
    temperature: float = Field(default=0.6, description="Temperature for generation")
    top_p: float = Field(default=0.9, description="Top-p sampling parameter")
    max_tokens: int = Field(default=1200, description="Maximum tokens to generate")
    repetition_penalty: float = Field(default=1.1, description="Repetition penalty")
    sample_rate: int = Field(default=24000, description="Audio sample rate")
    debug: bool = Field(default=False, description="Enable Orpheus debug mode")


# --- Together AI TTS Configuration ---
class TogetherTTSSettings(BaseModel):
    api_key: str = Field(default="", description="Together AI API key")
    api_url: str = Field(
        default="https://api.together.xyz/v1", description="Together AI API URL"
    )
    model: str = Field(
        default="canopylabs/orpheus-3b-0.1-ft",
        description="Together AI TTS model",
    )
    voice: str = Field(default="tara", description="Together AI voice")
    sample_rate: int = Field(default=24000, description="Audio sample rate")


# --- Call Flow Configuration ---
class CallFlowSettings(BaseModel):
    language_selection_enabled: bool = Field(
        default=False,
        description="Play a bilingual language-selection prompt at call start",
    )
    selection_retry_limit: int = Field(
        default=2,
        description="Number of retry prompts before defaulting to Spanish",
    )
    ringback_seconds: float = Field(
        default=2.0,
        description="Duration of the pre-agent ringback tone",
    )


# --- Settings Configuration ---
class Settings(BaseSettings):
    groq: GroqSettings = Field(default_factory=GroqSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    superlinked: SuperlinkedSettings = Field(default_factory=SuperlinkedSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    runpod: RunPodSettings = Field(default_factory=RunPodSettings)
    faster_whisper: FasterWhisperSettings = Field(default_factory=FasterWhisperSettings)
    orpheus: OrpheusTTSSettings = Field(default_factory=OrpheusTTSSettings)
    orpheus_spanish: OrpheusSpanishTTSSettings = Field(
        default_factory=OrpheusSpanishTTSSettings
    )
    together: TogetherTTSSettings = Field(default_factory=TogetherTTSSettings)
    call_flow: CallFlowSettings = Field(default_factory=CallFlowSettings)
    stt_model: str = Field(
        default="faster-whisper",
        description="STT provider to use (moonshine, whisper-groq, faster-whisper)",
    )
    tts_model: str = Field(
        default="orpheus-runpod",
        description="TTS provider to use (kokoro, together, orpheus-runpod)",
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
        case_sensitive=False,
        frozen=True,
    )


settings = Settings()
