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


# --- Groq Configuration ---
class OpenAISettings(BaseModel):
    api_key: str = Field(default="", description="OpenAI API Key")
    model: str = Field(default="gpt-4o-mini", description="OpenAI Model to use")


# --- Superlinked Configuration ---
class SuperlinkedSettings(BaseModel):
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding Model to use for Superlinked")
    area_min_value: int = Field(default=0, description="Minimum indexed room area in square meters")
    area_max_value: int = Field(default=100, description="Maximum indexed room area in square meters")
    price_min_value: int = Field(default=0, description="Minimum indexed orientative price in euros")
    price_max_value: int = Field(default=1000, description="Maximum indexed orientative price in euros")


# --- Knowledge Base Configuration ---
class KnowledgeBaseSettings(BaseModel):
    default_bundle_path: str = Field(
        default="data/blue_sardine_kb/2026-03-24",
        description="Default versioned knowledge bundle path to auto-ingest at startup",
    )
    auto_ingest_default_bundle: bool = Field(
        default=True, description="Automatically ingest the default knowledge bundle at startup"
    )

# --- Qdrant Configuration ---
class QdrantSettings(BaseModel):
    host: str = Field(default="qdrant", description="Qdrant Host")
    port: int = Field(default=6333, description="Qdrant Port")
    api_key: str = Field(default="", description="Qdrant API Key")
    use_https: bool = Field(default=False, description="Use HTTPS for Qdrant")


# --- Settings Configuration ---
class Settings(BaseSettings):
    groq: GroqSettings = Field(default_factory=GroqSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    superlinked: SuperlinkedSettings = Field(default_factory=SuperlinkedSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
        case_sensitive=False,
        frozen=True,
    )


settings = Settings()
