import json

from langchain.tools import tool  # type: ignore

from realtime_phone_agents.infrastructure.superlinked.service import (
    get_knowledge_search_service,
)


async def _search_hotel_kb(
    query: str,
    limit: int = 3,
    intent: str | None = None,
    hotel_id: str | None = None,
    doc_types: list[str] | None = None,
    section: str | None = None,
    room_type_id: str | None = None,
    policy_type: str | None = None,
    amenity_type: str | None = None,
    search_mode: str = "factual",
) -> str:
    knowledge_service = get_knowledge_search_service()
    response = await knowledge_service.search_knowledge(
        query=query,
        limit=limit,
        intent=intent,
        hotel_id=hotel_id,
        doc_types=doc_types,
        section=section,
        room_type_id=room_type_id,
        policy_type=policy_type,
        amenity_type=amenity_type,
        search_mode=search_mode,
    )
    return json.dumps(response, indent=2, ensure_ascii=False)


@tool
def search_property_mock_tool(location: str) -> str:
    """Retrieve placeholder hotel details for a given location."""
    return (
        "Blue Sardine Altea is a boutique accommodation near the sea and the old town. "
        "Use the real hotel knowledge tool for confirmed information."
    )


@tool
async def search_hotel_kb_tool(
    query: str,
    limit: int = 3,
    intent: str | None = None,
    hotel_id: str | None = None,
    doc_types: list[str] | None = None,
    section: str | None = None,
    room_type_id: str | None = None,
    policy_type: str | None = None,
    amenity_type: str | None = None,
    search_mode: str = "factual",
) -> str:
    """Search the hotel knowledge base with optional hotel-specific filters and search modes."""
    return await _search_hotel_kb(
        query=query,
        limit=limit,
        intent=intent,
        hotel_id=hotel_id,
        doc_types=doc_types,
        section=section,
        room_type_id=room_type_id,
        policy_type=policy_type,
        amenity_type=amenity_type,
        search_mode=search_mode,
    )


@tool
async def search_property_tool(
    query: str,
    limit: int = 3,
    intent: str | None = None,
    hotel_id: str | None = None,
    doc_types: list[str] | None = None,
    section: str | None = None,
    room_type_id: str | None = None,
    policy_type: str | None = None,
    amenity_type: str | None = None,
    search_mode: str = "factual",
) -> str:
    """Backward compatible alias for the hotel knowledge search tool."""
    return await _search_hotel_kb(
        query=query,
        limit=limit,
        intent=intent,
        hotel_id=hotel_id,
        doc_types=doc_types,
        section=section,
        room_type_id=room_type_id,
        policy_type=policy_type,
        amenity_type=amenity_type,
        search_mode=search_mode,
    )
