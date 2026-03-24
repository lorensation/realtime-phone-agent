from superlinked import framework as sl

from realtime_phone_agents.infrastructure.superlinked.constants import (
    ENTITY_TYPES,
    SOURCE_PRIORITIES,
    SUPPORTED_LANGUAGES,
    VERIFICATION_STATES,
)
from realtime_phone_agents.infrastructure.superlinked.index import (
    body_space,
    knowledge_index,
    knowledge_schema,
    title_space,
)


knowledge_search_query = (
    sl.Query(
        knowledge_index,
        weights={
            title_space: sl.Param("title_weight", default=1.0),
            body_space: sl.Param("body_weight", default=1.2),
        },
    )
    .find(knowledge_schema)
    .similar(title_space, sl.Param("title_query"))
    .similar(body_space, sl.Param("body_query"))
    .filter(
        knowledge_schema.entity_type
        == sl.Param("entity_type", options=ENTITY_TYPES)
    )
    .filter(
        knowledge_schema.room_type_id
        == sl.Param("room_type_id")
    )
    .filter(
        knowledge_schema.language
        == sl.Param("language", options=SUPPORTED_LANGUAGES)
    )
    .filter(
        knowledge_schema.verification_state
        == sl.Param("verification_state", options=VERIFICATION_STATES)
    )
    .filter(
        knowledge_schema.source_priority
        == sl.Param("source_priority", options=SOURCE_PRIORITIES)
    )
    .filter(
        knowledge_schema.area_sqm
        >= sl.Param("area_min")
    )
    .filter(
        knowledge_schema.base_price_eur
        <= sl.Param("price_max")
    )
    .limit(sl.Param("limit", default=3))
    .select_all()
)
