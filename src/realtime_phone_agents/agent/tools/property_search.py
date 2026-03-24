import json

from langchain.tools import tool

from realtime_phone_agents.infrastructure.superlinked.service import (
    get_knowledge_search_service,
)


async def _search_hotel_kb(query: str, limit: int = 3) -> str:
    knowledge_service = get_knowledge_search_service()
    response = await knowledge_service.search_knowledge(query=query, limit=limit)
    return json.dumps(response, indent=2, ensure_ascii=False)


@tool
def search_property_mock_tool(location: str) -> str:
    """Retrieve placeholder hotel details for a given location."""
    return (
        "Blue Sardine Altea is a boutique accommodation near the sea and the old town. "
        "Use the real hotel knowledge tool for confirmed information."
    )


@tool
async def search_hotel_kb_tool(query: str, limit: int = 3) -> str:
    """Search the Blue Sardine Altea hotel knowledge base with guardrails and sources."""
    return await _search_hotel_kb(query=query, limit=limit)


@tool
async def search_property_tool(query: str, limit: int = 3) -> str:
    """Backward compatible alias for the hotel knowledge search tool."""
    return await _search_hotel_kb(query=query, limit=limit)
