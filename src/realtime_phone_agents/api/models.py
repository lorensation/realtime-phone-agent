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
