from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievalFilters:
    hotel_id: str | None = None
    doc_types: list[str] = field(default_factory=list)
    section: str | None = None
    room_type_id: str | None = None
    policy_type: str | None = None
    amenity_type: str | None = None
    language: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hotel_id": self.hotel_id,
            "doc_types": list(self.doc_types),
            "section": self.section,
            "room_type_id": self.room_type_id,
            "policy_type": self.policy_type,
            "amenity_type": self.amenity_type,
            "language": self.language,
        }


@dataclass(slots=True)
class RetrievalContext:
    query: str
    intent: str | None
    search_mode: str = "factual"
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    slot_hints: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "retrieval.intent": self.intent or "",
            "retrieval.search_mode": self.search_mode,
            **{
                f"retrieval.filter.{key}": value
                for key, value in self.filters.as_dict().items()
                if value not in (None, [], "")
            },
        }
