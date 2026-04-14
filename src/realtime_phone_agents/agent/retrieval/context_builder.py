from __future__ import annotations

from realtime_phone_agents.agent.retrieval.models import RetrievalContext, RetrievalFilters
from realtime_phone_agents.config import settings
from realtime_phone_agents.knowledge.intent_router import (
    detect_amenity_type,
    detect_intent,
    detect_policy_type,
    extract_base_price_hint,
    extract_room_type_id,
    has_explicit_stay_dates,
)


FACTUAL_DOC_TYPES = [
    "structured_fact",
    "room_fact",
    "policy_fact",
    "faq",
    "document",
    "operational_note",
]
HANDOFF_DOC_TYPES = ["operational_note", "faq", "document"]
STYLE_DOC_TYPES = ["dialogue_exemplar"]
SECTION_ALIASES = {
    "operational": "operations",
    "operation": "operations",
    "operations": "operations",
    "service": "services",
    "services": "services",
    "policy": "policies",
    "policies": "policies",
    "room": "rooms",
    "rooms": "rooms",
}


def build_retrieval_context(
    query: str,
    *,
    explicit_intent: str | None = None,
    hotel_id: str | None = None,
    search_mode: str = "factual",
    room_type_id: str | None = None,
    policy_type: str | None = None,
    amenity_type: str | None = None,
    section: str | None = None,
    doc_types: list[str] | None = None,
    language: str | None = None,
) -> RetrievalContext:
    intent = explicit_intent or (
        detected.value if (detected := detect_intent(query)) is not None else None
    )
    resolved_room_type = room_type_id or extract_room_type_id(query)
    resolved_policy_type = policy_type or detect_policy_type(query)
    resolved_amenity_type = amenity_type or detect_amenity_type(query)
    resolved_section = _normalize_section(section or _section_from_intent(intent, query))
    resolved_doc_types = doc_types or _doc_types_for_mode(search_mode, query)

    filters = RetrievalFilters(
        hotel_id=hotel_id or settings.knowledge_base.default_hotel_id,
        doc_types=resolved_doc_types,
        section=resolved_section,
        room_type_id=resolved_room_type,
        policy_type=resolved_policy_type,
        amenity_type=resolved_amenity_type,
        language=language,
    )
    slot_hints = {
        "room_type_id": resolved_room_type,
        "policy_type": resolved_policy_type,
        "amenity_type": resolved_amenity_type,
        "price_hint": extract_base_price_hint(query),
        "has_explicit_stay_dates": has_explicit_stay_dates(query),
    }
    return RetrievalContext(
        query=query,
        intent=intent,
        search_mode=search_mode,
        filters=filters,
        slot_hints={key: value for key, value in slot_hints.items() if value is not None},
    )


def _doc_types_for_mode(search_mode: str, query: str) -> list[str]:
    lowered_query = query.lower()
    if search_mode == "style":
        return STYLE_DOC_TYPES
    if search_mode == "handoff":
        return HANDOFF_DOC_TYPES
    if "taxi" in lowered_query or "gps" in lowered_query or "direccion exacta" in lowered_query:
        return ["operational_note", "faq", "document", "structured_fact"]
    if any(
        phrase in lowered_query
        for phrase in ("que hay para visitar", "que ver", "what to visit", "nearby")
    ):
        return ["document", "faq", "structured_fact", "operational_note"]
    return FACTUAL_DOC_TYPES


def _section_from_intent(intent: str | None, query: str) -> str | None:
    lowered_query = query.lower()
    if "taxi" in lowered_query or "gps" in lowered_query or "direccion exacta" in lowered_query:
        return "operations"
    if any(
        phrase in lowered_query
        for phrase in ("que hay para visitar", "que ver", "what to visit", "nearby")
    ):
        return "location"
    if "parking" in lowered_query or "aparc" in lowered_query:
        return "parking"
    if intent == "policies":
        return "policies"
    if intent == "location_and_parking":
        return "location"
    if intent == "room_selection":
        return "rooms"
    if intent == "availability_pricing":
        return "pricing"
    if intent == "special_requests":
        return "operations"
    return None


def _normalize_section(section: str | None) -> str | None:
    if section is None:
        return None
    normalized = section.strip().lower().replace("-", "_")
    normalized = normalized.replace("_note", "")
    return SECTION_ALIASES.get(normalized, normalized)
