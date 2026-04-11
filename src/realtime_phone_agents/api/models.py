from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request model for ingesting a versioned hotel knowledge bundle."""

    bundle_path: str = Field(
        ..., description="Path to the versioned knowledge bundle directory"
    )


class SearchRequest(BaseModel):
    """Request model for searching hotel knowledge."""

    query: str = Field(
        ..., description="Natural language query for hotel knowledge search"
    )
    limit: int = Field(
        default=3, ge=1, le=10, description="Maximum number of results to return"
    )
    intent: str | None = Field(
        default=None, description="Optional explicit search intent override"
    )
    language: str | None = Field(
        default=None, description="Optional language filter for debugging or tests"
    )
    hotel_id: str | None = Field(
        default=None, description="Optional hotel identifier filter"
    )
    doc_types: list[str] | None = Field(
        default=None, description="Optional list of document types to search"
    )
    section: str | None = Field(
        default=None, description="Optional section filter such as policies or rooms"
    )
    room_type_id: str | None = Field(
        default=None, description="Optional explicit room type filter"
    )
    policy_type: str | None = Field(
        default=None, description="Optional policy subtype filter"
    )
    amenity_type: str | None = Field(
        default=None, description="Optional amenity subtype filter"
    )
    search_mode: str = Field(
        default="factual",
        description="Retrieval mode: factual, handoff, or style",
    )
