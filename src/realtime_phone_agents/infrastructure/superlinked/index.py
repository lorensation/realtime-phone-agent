# ruff: noqa: E402

import os
from pathlib import Path

from realtime_phone_agents.config import settings

LOCAL_MODEL_CACHE_DIR = (Path(".cache") / "sentence_transformers").resolve()
os.environ.setdefault("MODEL_CACHE_DIR", LOCAL_MODEL_CACHE_DIR.as_posix())
os.environ.setdefault("APP_ID", settings.knowledge_base.collection_name)

from superlinked import framework as sl


class Knowledge(sl.Schema):
    """Schema for hotel knowledge entries."""

    id: sl.IdField
    title: sl.String
    body: sl.String
    entity_type: sl.String
    hotel_id: sl.String
    hotel_name: sl.String
    brand_name: sl.String
    source_url: sl.String
    source_type: sl.String
    section: sl.String
    doc_type: sl.String
    room_type: sl.String
    amenity_type: sl.String
    policy_type: sl.String
    faq_id: sl.String
    dialogue_id: sl.String
    confidence: sl.String
    requires_handoff: sl.Integer
    updated_at: sl.String
    room_type_id: sl.String
    language: sl.String
    source_priority: sl.String
    verification_state: sl.String
    area_sqm: sl.Integer
    adults_max: sl.Integer
    base_price_eur: sl.Integer
    version: sl.String
    sources: sl.StringList
    tags: sl.StringList


knowledge_schema = Knowledge()


title_space = sl.TextSimilaritySpace(
    text=knowledge_schema.title,
    model=settings.superlinked.embedding_model,
)

body_space = sl.TextSimilaritySpace(
    text=knowledge_schema.body,
    model=settings.superlinked.embedding_model,
)

area_space = sl.NumberSpace(
    number=knowledge_schema.area_sqm,
    min_value=settings.superlinked.area_min_value,
    max_value=settings.superlinked.area_max_value,
    mode=sl.Mode.MAXIMUM,
)

price_space = sl.NumberSpace(
    number=knowledge_schema.base_price_eur,
    min_value=settings.superlinked.price_min_value,
    max_value=settings.superlinked.price_max_value,
    mode=sl.Mode.MINIMUM,
)

knowledge_index = sl.Index(
    spaces=[title_space, body_space, area_space, price_space],
    fields=[
        knowledge_schema.title,
        knowledge_schema.body,
        knowledge_schema.entity_type,
        knowledge_schema.hotel_id,
        knowledge_schema.hotel_name,
        knowledge_schema.brand_name,
        knowledge_schema.source_url,
        knowledge_schema.source_type,
        knowledge_schema.section,
        knowledge_schema.doc_type,
        knowledge_schema.room_type,
        knowledge_schema.amenity_type,
        knowledge_schema.policy_type,
        knowledge_schema.faq_id,
        knowledge_schema.dialogue_id,
        knowledge_schema.confidence,
        knowledge_schema.requires_handoff,
        knowledge_schema.updated_at,
        knowledge_schema.room_type_id,
        knowledge_schema.language,
        knowledge_schema.source_priority,
        knowledge_schema.verification_state,
        knowledge_schema.area_sqm,
        knowledge_schema.adults_max,
        knowledge_schema.base_price_eur,
        knowledge_schema.version,
        knowledge_schema.sources,
        knowledge_schema.tags,
    ],
)
