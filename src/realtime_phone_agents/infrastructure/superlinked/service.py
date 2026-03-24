from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from superlinked import framework as sl

from realtime_phone_agents.config import settings
from realtime_phone_agents.knowledge import (
    Intent,
    SourcePriority,
    VerificationState,
    detect_intent,
    extract_area_sqm_hint,
    extract_base_price_hint,
    extract_room_type_id,
    has_explicit_stay_dates,
    is_unverified_amenity_question,
    load_knowledge_bundle,
    normalize_knowledge_bundle,
)
from realtime_phone_agents.knowledge.models import HotelKnowledgeBundle, KnowledgeEntry
from realtime_phone_agents.infrastructure.superlinked.index import knowledge_index, knowledge_schema
from realtime_phone_agents.infrastructure.superlinked.query import knowledge_search_query


class KnowledgeSearchService:
    """Service for ingesting and searching hotel knowledge using Superlinked."""

    def __init__(
        self,
        qdrant_host: str | None,
        qdrant_port: int | None,
        qdrant_api_key: str | None,
        qdrant_use_https: bool | None,
        force_in_memory: bool = False,
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_api_key = qdrant_api_key
        self.qdrant_use_https = qdrant_use_https
        self.force_in_memory = force_in_memory

        self.app = None
        self.source = None
        self.bundle: HotelKnowledgeBundle | None = None
        self.loaded_bundle_path: str | None = None

        self._setup_app()

    def _setup_app(self) -> None:
        """Setup Superlinked with Qdrant when available, otherwise fallback to memory."""
        if self.force_in_memory:
            self._setup_with_memory()
            return
        try:
            self._setup_with_qdrant()
        except Exception as exc:
            logger.warning(f"Qdrant setup failed, falling back to InMemoryExecutor: {exc}")
            self._setup_with_memory()

    def _setup_with_qdrant(self) -> None:
        protocol = "https" if self.qdrant_use_https else "http"
        qdrant_url = f"{protocol}://{self.qdrant_host}:{self.qdrant_port}"

        vector_db = sl.QdrantVectorDatabase(
            url=qdrant_url,
            api_key=self.qdrant_api_key,
            default_query_limit=5,
        )

        logger.info(f"Connecting to Qdrant at {qdrant_url} ...")

        self.source = sl.RestSource(
            knowledge_schema, parser=sl.DataFrameParser(schema=knowledge_schema)
        )

        search_descriptor = sl.RestDescriptor(query_path="/search")
        rest_query = sl.RestQuery(search_descriptor, knowledge_search_query)

        executor = sl.RestExecutor(
            sources=[self.source],
            indices=[knowledge_index],
            queries=[rest_query],
            vector_database=vector_db,
        )

        self.app = executor.run()
        logger.info("KnowledgeSearchService initialized with Qdrant RestExecutor")

    def _setup_with_memory(self) -> None:
        self.source = sl.InMemorySource(
            knowledge_schema, parser=sl.DataFrameParser(schema=knowledge_schema)
        )
        executor = sl.InMemoryExecutor(sources=[self.source], indices=[knowledge_index])
        self.app = executor.run()
        logger.info("KnowledgeSearchService initialized with InMemoryExecutor")

    def ingest_default_bundle_if_configured(self) -> None:
        if not settings.knowledge_base.auto_ingest_default_bundle:
            return

        default_path = Path(settings.knowledge_base.default_bundle_path)
        if not default_path.exists():
            logger.warning(f"Default knowledge bundle path not found: {default_path}")
            return
        if self.loaded_bundle_path == str(default_path.resolve()):
            return
        self.ingest_knowledge_bundle(default_path)

    def ingest_knowledge_bundle(self, bundle_path: str | Path) -> dict[str, Any]:
        bundle = load_knowledge_bundle(bundle_path)
        entries = normalize_knowledge_bundle(bundle)
        dataframe = pd.DataFrame([self._entry_to_row(entry) for entry in entries])
        self.source.put([dataframe])

        self.bundle = bundle
        self.loaded_bundle_path = str(Path(bundle_path).resolve())

        logger.info(
            f"Ingested knowledge bundle {bundle.manifest.kb_version} with {len(entries)} entries"
        )
        return {
            "bundle_path": self.loaded_bundle_path,
            "version": bundle.manifest.kb_version,
            "entry_count": len(entries),
        }

    def _entry_to_row(self, entry: KnowledgeEntry) -> dict[str, Any]:
        row = entry.model_dump(mode="json")
        row["room_type_id"] = row["room_type_id"] or ""
        return row

    def _result_to_entries(self, result) -> list[dict[str, Any]]:
        entries = result.model_dump()["entries"]
        cleaned_entries: list[dict[str, Any]] = []
        for entry in entries:
            fields = entry["fields"]
            fields["id"] = entry["id"]
            if not fields.get("room_type_id"):
                fields["room_type_id"] = None
            cleaned_entries.append(fields)
        return cleaned_entries

    def _entity_type_for_intent(self, intent: Intent | None, query: str) -> str | None:
        if intent == Intent.ROOM_SELECTION:
            return "room_type"
        if intent == Intent.POLICIES:
            return "policy"
        if intent == Intent.SPECIAL_REQUESTS:
            return "service"
        if intent == Intent.AVAILABILITY_PRICING:
            return "pricing"
        if intent == Intent.LOCATION_AND_PARKING:
            lowered_query = query.lower()
            if any(keyword in lowered_query for keyword in ("parking", "aparc", "la mar", "station", "tren")):
                return "parking"
            return "location"
        return None

    def _resolve_language_filter(self, language: str | None) -> str | None:
        if self.bundle and language in self.bundle.supported_languages:
            return language
        return None

    async def _run_search(
        self,
        query: str,
        limit: int,
        entity_type: str | None,
        room_type_id: str | None,
        language: str | None,
        verification_state: str | None,
        source_priority: str | None,
        area_hint: int | None,
        price_hint: int | None,
    ) -> list[dict[str, Any]]:
        query_params: dict[str, Any] = {
            "title_query": query,
            "body_query": query,
            "title_weight": 1.0,
            "body_weight": 1.2,
            "limit": limit,
            "entity_type": entity_type,
            "room_type_id": room_type_id,
            "language": language,
            "verification_state": verification_state,
            "source_priority": source_priority,
            "area_min": area_hint,
            "price_max": price_hint,
        }

        results = await self.app.async_query(knowledge_search_query, **query_params)
        return self._result_to_entries(results)

    def _build_guardrail_notes(
        self,
        query: str,
        resolved_intent: Intent | None,
        results: list[dict[str, Any]],
    ) -> list[str]:
        notes: list[str] = []
        if is_unverified_amenity_question(query):
            notes.append(
                "La base publica no confirma botellas de agua de cortesia. Di que no esta confirmado y ofrece telefono o email."
            )
        if resolved_intent == Intent.AVAILABILITY_PRICING and not has_explicit_stay_dates(query):
            notes.append(
                "Pide fechas exactas antes de cotizar. Sin motor de reservas integrado, solo comparte precios orientativos."
            )

        if any(
            result["verification_state"] == VerificationState.INTERNAL_UNVALIDATED.value
            for result in results
        ):
            notes.append(
                "Presenta cualquier precio interno como orientativo desde X EUR y recomienda confirmar en web o por contacto."
            )
            logger.warning("Using internal_unvalidated pricing in hotel knowledge response")

        if any(result["verification_state"] == VerificationState.THIRD_PARTY.value for result in results):
            notes.append(
                "Indica que esa tipologia proviene de canales externos y necesita confirmacion directa."
            )

        if not results:
            notes.append(
                "Si no tienes el dato confirmado, dilo claramente y ofrece telefono o email del alojamiento."
            )
        return notes

    async def search_knowledge(
        self,
        query: str,
        limit: int = 3,
        intent: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        if self.bundle is None:
            self.ingest_default_bundle_if_configured()
        if self.bundle is None:
            raise RuntimeError("No hotel knowledge bundle has been ingested")

        resolved_intent = Intent(intent) if intent in {item.value for item in Intent} else detect_intent(query)
        room_type_id = extract_room_type_id(query)
        area_hint = extract_area_sqm_hint(query)
        price_hint = extract_base_price_hint(query)
        entity_type = self._entity_type_for_intent(resolved_intent, query)
        language_filter = self._resolve_language_filter(language)

        results = await self._run_search(
            query=query,
            limit=limit,
            entity_type=entity_type,
            room_type_id=room_type_id,
            language=language_filter,
            verification_state=None,
            source_priority=None,
            area_hint=area_hint,
            price_hint=price_hint,
        )

        if not results and room_type_id:
            results = await self._run_search(
                query=query,
                limit=limit,
                entity_type=entity_type,
                room_type_id=None,
                language=language_filter,
                verification_state=None,
                source_priority=None,
                area_hint=area_hint,
                price_hint=price_hint,
            )

        if not results and entity_type is not None:
            results = await self._run_search(
                query=query,
                limit=limit,
                entity_type=None,
                room_type_id=room_type_id,
                language=language_filter,
                verification_state=None,
                source_priority=None,
                area_hint=area_hint,
                price_hint=price_hint,
            )

        guardrail_notes = self._build_guardrail_notes(query, resolved_intent, results)

        return {
            "query": query,
            "resolved_intent": resolved_intent.value if resolved_intent else None,
            "room_type_id": room_type_id,
            "language_filter": language_filter,
            "result_count": len(results),
            "guardrail_notes": guardrail_notes,
            "fallback_contact": self.bundle.contact.model_dump(mode="json"),
            "results": results,
        }


_knowledge_service: KnowledgeSearchService | None = None


def get_knowledge_search_service(
    qdrant_host: str | None = settings.qdrant.host,
    qdrant_port: int | None = settings.qdrant.port,
    qdrant_api_key: str | None = settings.qdrant.api_key,
    qdrant_use_https: bool | None = settings.qdrant.use_https,
    force_in_memory: bool = False,
) -> KnowledgeSearchService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeSearchService(
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            qdrant_api_key=qdrant_api_key,
            qdrant_use_https=qdrant_use_https,
            force_in_memory=force_in_memory,
        )
        _knowledge_service.ingest_default_bundle_if_configured()
    return _knowledge_service
