from __future__ import annotations

import math
import re
from collections.abc import Iterable

from realtime_phone_agents.knowledge.intent_router import (
    detect_amenity_type,
    detect_policy_type,
    extract_room_type_id,
)
from realtime_phone_agents.knowledge.models import (
    HotelKnowledgeBundle,
    KnowledgeEntry,
    SourcePriority,
    VerificationState,
)


MAX_CHUNK_WORDS = 220
CHUNK_OVERLAP_WORDS = 40


def normalize_knowledge_bundle(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    entries.extend(_normalize_property_entries(bundle))
    entries.extend(_normalize_service_entries(bundle))
    entries.extend(_normalize_policy_entries(bundle))
    entries.extend(_normalize_room_type_entries(bundle))
    entries.extend(_normalize_pricing_entries(bundle))
    entries.extend(_normalize_document_entries(bundle))
    entries.extend(_normalize_faq_entries(bundle))
    entries.extend(_normalize_dialogue_entries(bundle))
    entries.extend(_normalize_operational_note_entries(bundle))
    return entries


def _hotel_metadata(bundle: HotelKnowledgeBundle) -> dict[str, str]:
    return {
        "hotel_id": "blue_sardine_altea",
        "hotel_name": bundle.hotel.property.name,
        "brand_name": "Blue Sardine",
        "updated_at": bundle.manifest.generated_at,
    }


def _build_entry(
    *,
    bundle: HotelKnowledgeBundle,
    entry_id: str,
    title: str,
    body: str,
    entity_type: str,
    section: str,
    doc_type: str,
    source_url: str,
    source_type: str,
    source_priority: SourcePriority,
    verification_state: VerificationState,
    language: str = "es-ES",
    room_type_id: str | None = None,
    amenity_type: str | None = None,
    policy_type: str | None = None,
    faq_id: str | None = None,
    dialogue_id: str | None = None,
    confidence: str = "confirmed",
    requires_handoff: bool = False,
    area_sqm: int = 0,
    adults_max: int = 0,
    base_price_eur: int = 0,
    sources: list[str] | None = None,
    tags: list[str] | None = None,
) -> KnowledgeEntry:
    hotel_meta = _hotel_metadata(bundle)
    return KnowledgeEntry(
        id=entry_id,
        title=title,
        body=body,
        entity_type=entity_type,
        hotel_id=hotel_meta["hotel_id"],
        hotel_name=hotel_meta["hotel_name"],
        brand_name=hotel_meta["brand_name"],
        language=language,
        source_url=source_url,
        source_type=source_type,
        section=section,
        doc_type=doc_type,
        room_type=room_type_id,
        amenity_type=amenity_type,
        policy_type=policy_type,
        faq_id=faq_id,
        dialogue_id=dialogue_id,
        confidence=confidence,
        requires_handoff=requires_handoff,
        updated_at=hotel_meta["updated_at"],
        room_type_id=room_type_id,
        source_priority=source_priority,
        verification_state=verification_state,
        area_sqm=area_sqm,
        adults_max=adults_max,
        base_price_eur=base_price_eur,
        version=bundle.manifest.kb_version,
        sources=sources or [source_url],
        tags=tags or [],
    )


def _normalize_property_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    hotel = bundle.hotel
    contact = hotel.property.contact
    return [
        _build_entry(
            bundle=bundle,
            entry_id="overview_property",
            title=hotel.property.name,
            body=(
                f"{hotel.property.name} es un alojamiento boutique en un antiguo barrio de "
                f"pescadores, cerca del mar y al inicio del casco historico de Altea. "
                f"Direccion publicada: {hotel.property.address_public}."
            ),
            entity_type="overview",
            section="overview",
            doc_type="structured_fact",
            source_url="https://bluesardinealtea.com/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            tags=["overview", "location", "boutique"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="location_address",
            title="Ubicacion y direccion",
            body=(
                f"El alojamiento publica la direccion {hotel.property.address_public} y lo "
                "describe como cercano al mar y al casco historico de Altea."
            ),
            entity_type="location",
            section="location",
            doc_type="structured_fact",
            source_url="https://bluesardinealtea.com/en/contact/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            tags=["location", "address"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="contact_primary",
            title="Contacto del alojamiento",
            body=(
                f"Telefono de contacto: {contact.phone}. Email: {contact.email}. Si falta "
                "un dato confirmado, se recomienda confirmarlo por telefono o email."
            ),
            entity_type="contact",
            section="contact",
            doc_type="structured_fact",
            source_url="https://bluesardinealtea.com/en/contact/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            tags=["contact"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="parking_public_free",
            title="Parking publico gratuito",
            body=(
                "No hay parking dentro del alojamiento. Hay parking publico gratuito a unos "
                f"{hotel.parking.public_free_parking.walking_distance_m} metros andando. "
                f"Referencia publicada: {hotel.parking.public_free_parking.location_note}. "
                f"Nota: {hotel.parking.public_free_parking.liability_note}."
            ),
            entity_type="parking",
            section="parking",
            doc_type="structured_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            amenity_type="parking",
            tags=["parking", "location"],
        ),
    ]


def _normalize_service_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    services = bundle.hotel.services_and_facilities
    return [
        _entry_from_token_list(
            entry_id="service_experience",
            title="Servicios de experiencia",
            body_prefix="Servicios destacados",
            entity_type="service",
            section="services",
            tokens=services.experience,
            bundle=bundle,
            amenity_type="guest_experience",
            tags=["services", "experience"],
        ),
        _entry_from_token_list(
            entry_id="service_housekeeping",
            title="Limpieza y confort",
            body_prefix="Limpieza y confort",
            entity_type="service",
            section="services",
            tokens=services.housekeeping,
            bundle=bundle,
            amenity_type="housekeeping",
            tags=["services", "housekeeping"],
        ),
        _entry_from_token_list(
            entry_id="service_facilities",
            title="Equipamiento general",
            body_prefix="Equipamiento general",
            entity_type="service",
            section="services",
            tokens=services.in_room_and_property,
            bundle=bundle,
            amenity_type="facilities",
            tags=["services", "facilities"],
        ),
    ]


def _normalize_policy_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    policies = bundle.hotel.policies
    return [
        _build_entry(
            bundle=bundle,
            entry_id="policy_checkin_checkout",
            title="Check-in y check-out",
            body=(
                f"El check-in es a partir de las {policies.check_in} y el check-out debe "
                f"hacerse antes de las {policies.check_out}."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="checkin",
            tags=["policy", "checkin", "checkout"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_luggage",
            title="Consigna y salida",
            body=(
                "Hay taquillas gratuitas para equipaje y un sistema de buzon para dejar "
                "las llaves a la salida."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="luggage",
            tags=["policy", "luggage"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_adults_children",
            title="Politica de adultos y menores",
            body=(
                "El alojamiento esta orientado a adultos y admite ninos a partir de "
                f"{policies.adults_and_children.children_allowed_from_age} anos."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="children",
            tags=["policy", "adults", "children"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_smoke_free",
            title="Politica de humo",
            body="El establecimiento es smoke-free y fumar puede conllevar cargos.",
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="smoking",
            tags=["policy", "smoking"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_pets",
            title="Mascotas",
            body="No se permiten mascotas.",
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="pets",
            tags=["policy", "pets"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_bicycles_scooters",
            title="Bicicletas y patinetes",
            body=(
                "No se permiten bicicletas ni patinetes electricos dentro del "
                "alojamiento ni en las habitaciones."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="mobility",
            tags=["policy", "bicycles", "scooters"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_reservation_hours",
            title="Horario de reservas",
            body=(
                f"Atencion telefonica: {policies.reservation_hours.phone_support}. "
                f"Reservas web: {policies.reservation_hours.website_booking}."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="reservation_hours",
            tags=["policy", "reservations"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_payment_cancellation",
            title="Pago y cancelacion",
            body=(
                "Se requiere tarjeta valida. La cancelacion gratuita aplica hasta 5 dias "
                "antes de la llegada. No se permiten cambios de fecha dentro de los 5 "
                "dias previos. En tarifa no reembolsable no se permiten cancelaciones ni "
                "modificaciones. La fuerza mayor queda sujeta a revision del equipo de "
                "reservas."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="cancellation",
            tags=["policy", "payment", "cancellation"],
        ),
        _build_entry(
            bundle=bundle,
            entry_id="policy_damages",
            title="Cargos por danos y perdidas",
            body=(
                "Se aplican cargos por danos y perdidas. Toalla pequena: 10 EUR. Toalla "
                "grande: 15 EUR. Los elementos decorativos se cobran segun su valor."
            ),
            entity_type="policy",
            section="policies",
            doc_type="policy_fact",
            source_url="https://bluesardinealtea.com/en/general-conditions/",
            source_type="official_site",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            policy_type="damages",
            tags=["policy", "damages"],
        ),
    ]


def _normalize_room_type_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for room_type in bundle.room_types.room_types:
        details: list[str] = []
        if room_type.area_sqm:
            details.append(f"{room_type.area_sqm} m2")
        details.append(f"hasta {room_type.occupancy.adults_max} adultos")
        details.append(f"cama {room_type.bed}")
        if room_type.layout:
            details.append(
                "distribucion: "
                + ", ".join(_humanize_token(token) for token in room_type.layout)
            )
        if room_type.highlights:
            details.append(
                "destaca por "
                + ", ".join(_humanize_token(token) for token in room_type.highlights)
            )
        if room_type.features:
            details.append(
                "incluye "
                + ", ".join(_humanize_token(token) for token in room_type.features)
            )
        entries.append(
            _build_entry(
                bundle=bundle,
                entry_id=f"room_type_{room_type.id}",
                title=room_type.display_name_es,
                body=". ".join(details) + ".",
                entity_type="room_type",
                section="rooms",
                doc_type="room_fact",
                source_url="https://bluesardinealtea.com/",
                source_type="official_site",
                source_priority=SourcePriority.OFFICIAL,
                verification_state=VerificationState.OFFICIAL,
                room_type_id=room_type.id,
                area_sqm=room_type.area_sqm or 0,
                adults_max=room_type.occupancy.adults_max,
                tags=["room_type", room_type.id],
            )
        )

    for extension in bundle.room_types.room_type_extensions:
        entries.append(
            _build_entry(
                bundle=bundle,
                entry_id=f"room_type_extension_{extension.id}",
                title=extension.display_name_es,
                body=(
                    f"{extension.display_name_es} aparece en canales externos, pero no "
                    "esta descrita con detalle en la web principal. "
                    f"Nota: {extension.notes}"
                ),
                entity_type="room_type",
                section="rooms",
                doc_type="room_fact",
                source_url="https://www.google.com/travel/hotels",
                source_type="third_party",
                source_priority=SourcePriority.THIRD_PARTY,
                verification_state=VerificationState.THIRD_PARTY,
                room_type_id=extension.id,
                confidence="unconfirmed",
                requires_handoff=extension.needs_internal_validation,
                tags=["room_type", extension.id, "unverified"],
            )
        )
    return entries


def _normalize_pricing_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    pricing = bundle.pricing_inventory.pricing_and_inventory_internal
    room_display_names = {
        room_type.id: room_type.display_name_es
        for room_type in bundle.room_types.room_types
    }
    room_display_names.update(
        {
            room_type.id: room_type.display_name_es
            for room_type in bundle.room_types.room_type_extensions
        }
    )

    entries = [
        _build_entry(
            bundle=bundle,
            entry_id="pricing_summary",
            title="Precios orientativos e inventario interno",
            body=(
                "Los precios base internos son orientativos, pueden variar por temporada "
                "y ocupacion, y requieren confirmacion final. La configuracion interna "
                f"actual suma {pricing.inventory_sum_units} unidades y mantiene una "
                f"discrepancia interna de {pricing.inventory_gap_units} unidad frente a "
                "la referencia externa de 21."
            ),
            entity_type="pricing",
            section="pricing",
            doc_type="structured_fact",
            source_url="internal://pricing_inventory_internal",
            source_type="internal_config",
            source_priority=SourcePriority.INTERNAL_UNVALIDATED,
            verification_state=VerificationState.INTERNAL_UNVALIDATED,
            confidence="orientative",
            requires_handoff=True,
            tags=["pricing", "inventory"],
        )
    ]

    for item in pricing.inventory_breakdown:
        entries.append(
            _build_entry(
                bundle=bundle,
                entry_id=f"pricing_{item.room_type_id}",
                title=f"Precio orientativo {room_display_names[item.room_type_id]}",
                body=(
                    f"Precio base interno orientativo desde {item.base_price_eur} EUR "
                    f"para {room_display_names[item.room_type_id]}. Configuracion "
                    f"actual: {item.units} unidades. Dato interno pendiente de "
                    "validacion y sujeto a temporada y ocupacion."
                ),
                entity_type="pricing",
                section="pricing",
                doc_type="structured_fact",
                source_url="internal://pricing_inventory_internal",
                source_type="internal_config",
                source_priority=SourcePriority.INTERNAL_UNVALIDATED,
                verification_state=VerificationState.INTERNAL_UNVALIDATED,
                room_type_id=item.room_type_id,
                base_price_eur=item.base_price_eur,
                confidence="orientative",
                requires_handoff=True,
                tags=["pricing", item.room_type_id],
            )
        )
    return entries


def _normalize_document_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for document in bundle.documents.documents:
        entity_type = _classify_entity_type(
            text=" ".join(
                [document.title, document.body, " ".join(document.metadata.tags)]
            )
        )
        chunks = _split_body(document.body)
        for index, chunk in enumerate(chunks, start=1):
            chunk_suffix = f"_chunk_{index}" if len(chunks) > 1 else ""
            room_type_id = extract_room_type_id(document.title + " " + document.body)
            policy_type = detect_policy_type(document.title + " " + document.body)
            amenity_type = detect_amenity_type(document.title + " " + document.body)
            entries.append(
                _build_entry(
                    bundle=bundle,
                    entry_id=f"document_{document.doc_id}{chunk_suffix}",
                    title=document.title,
                    body=chunk,
                    entity_type=entity_type,
                    section=document.metadata.section or _section_for_entity_type(entity_type),
                    doc_type=document.metadata.doc_type,
                    source_url=document.metadata.source_urls[0],
                    source_type=document.metadata.source_type,
                    source_priority=document.metadata.source_priority,
                    verification_state=_priority_to_verification(
                        document.metadata.source_priority
                    ),
                    room_type_id=room_type_id,
                    amenity_type=amenity_type,
                    policy_type=policy_type,
                    language=document.language,
                    sources=document.metadata.source_urls,
                    tags=document.metadata.tags,
                )
            )
    return entries


def _normalize_faq_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for index, item in enumerate(bundle.faq.faq, start=1):
        combined_text = f"{item.q} {item.a}"
        entity_type = _classify_entity_type(combined_text)
        faq_id = item.faq_id or f"faq_{index}"
        entries.append(
            _build_entry(
                bundle=bundle,
                entry_id=faq_id,
                title=item.q,
                body=item.a,
                entity_type=entity_type,
                section=item.section or _section_for_entity_type(entity_type),
                doc_type="faq",
                source_url=(item.sources[0] if item.sources else "https://bluesardinealtea.com/"),
                source_type="official_site",
                source_priority=SourcePriority.OFFICIAL,
                verification_state=VerificationState.OFFICIAL,
                room_type_id=extract_room_type_id(combined_text),
                amenity_type=item.amenity_type or detect_amenity_type(combined_text),
                policy_type=item.policy_type or detect_policy_type(combined_text),
                faq_id=faq_id,
                requires_handoff=item.requires_handoff,
                sources=item.sources,
                tags=["faq", entity_type],
            )
        )
    return entries


def _normalize_dialogue_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for dialogue in bundle.dialogues.dialogues:
        room_type_id = extract_room_type_id(dialogue.body)
        entries.append(
            _build_entry(
                bundle=bundle,
                entry_id=f"dialogue_{dialogue.dialogue_id}",
                title=f"Dialogo {dialogue.dialogue_id}: {dialogue.intent}",
                body=dialogue.body,
                entity_type="dialogue",
                section="operations",
                doc_type="dialogue_exemplar",
                source_url=dialogue.sources[0] if dialogue.sources else "internal://dialogues",
                source_type="internal_dialogue",
                source_priority=SourcePriority.INTERNAL_VALIDATED,
                verification_state=VerificationState.INTERNAL_VALIDATED,
                language=dialogue.language,
                room_type_id=room_type_id,
                amenity_type=detect_amenity_type(dialogue.body),
                policy_type=detect_policy_type(dialogue.body),
                dialogue_id=dialogue.dialogue_id,
                confidence="style_reference",
                requires_handoff=dialogue.requires_handoff,
                sources=dialogue.sources,
                tags=["dialogue", dialogue.intent, *dialogue.tags],
            )
        )
    return entries


def _normalize_operational_note_entries(
    bundle: HotelKnowledgeBundle,
) -> list[KnowledgeEntry]:
    return [
        _build_entry(
            bundle=bundle,
            entry_id=f"operational_note_{note.note_id}",
            title=note.title,
            body=note.body,
            entity_type="operational_note",
            section=note.section,
            doc_type="operational_note",
            source_url=note.source_urls[0] if note.source_urls else "internal://operations",
            source_type="internal_operational_note",
            source_priority=SourcePriority.INTERNAL_VALIDATED,
            verification_state=VerificationState.INTERNAL_VALIDATED,
            amenity_type=detect_amenity_type(note.body),
            policy_type=detect_policy_type(note.body),
            confidence=note.confidence,
            requires_handoff=note.requires_handoff,
            sources=note.source_urls,
            tags=["operational_note", note.section, *note.tags],
        )
        for note in bundle.operational_notes.notes
    ]


def _entry_from_token_list(
    entry_id: str,
    title: str,
    body_prefix: str,
    entity_type: str,
    section: str,
    tokens: Iterable[str],
    bundle: HotelKnowledgeBundle,
    amenity_type: str,
    tags: list[str],
) -> KnowledgeEntry:
    body = (
        body_prefix + ": " + ", ".join(_humanize_token(token) for token in tokens) + "."
    )
    return _build_entry(
        bundle=bundle,
        entry_id=entry_id,
        title=title,
        body=body,
        entity_type=entity_type,
        section=section,
        doc_type="structured_fact",
        source_url="https://bluesardinealtea.com/",
        source_type="official_site",
        source_priority=SourcePriority.OFFICIAL,
        verification_state=VerificationState.OFFICIAL,
        amenity_type=amenity_type,
        tags=tags,
    )


def _humanize_token(token: str) -> str:
    return token.replace("_", " ")


def _priority_to_verification(priority: SourcePriority) -> VerificationState:
    if priority == SourcePriority.OFFICIAL:
        return VerificationState.OFFICIAL
    if priority == SourcePriority.INTERNAL_VALIDATED:
        return VerificationState.INTERNAL_VALIDATED
    if priority == SourcePriority.INTERNAL_UNVALIDATED:
        return VerificationState.INTERNAL_UNVALIDATED
    return VerificationState.THIRD_PARTY


def _classify_entity_type(text: str) -> str:
    normalized_text = re.sub(r"\s+", " ", text.lower())
    if any(
        keyword in normalized_text
        for keyword in ("parking", "aparcamiento", "calle la mar")
    ):
        return "parking"
    if any(
        keyword in normalized_text
        for keyword in ("direccion", "ubicacion", "casco historico", "mar", "playa")
    ):
        return "location"
    if any(
        keyword in normalized_text
        for keyword in (
            "check-in",
            "check in",
            "check-out",
            "mascotas",
            "pets",
            "cancel",
            "smoke",
            "adultos",
        )
    ):
        return "policy"
    if any(
        keyword in normalized_text
        for keyword in ("precio", "price", "tarifa", "booking", "reservar")
    ):
        return "pricing"
    if any(
        keyword in normalized_text
        for keyword in ("celebracion", "birthday", "aniversario", "servicio")
    ):
        return "service"
    if extract_room_type_id(normalized_text):
        return "room_type"
    return "overview"


def _section_for_entity_type(entity_type: str) -> str:
    mapping = {
        "parking": "parking",
        "location": "location",
        "policy": "policies",
        "pricing": "pricing",
        "service": "services",
        "room_type": "rooms",
        "contact": "contact",
    }
    return mapping.get(entity_type, "overview")


def _split_body(text: str) -> list[str]:
    words = text.split()
    if len(words) <= MAX_CHUNK_WORDS:
        return [text]

    chunks: list[str] = []
    step = max(MAX_CHUNK_WORDS - CHUNK_OVERLAP_WORDS, 1)
    total_chunks = math.ceil(len(words) / step)
    for index in range(total_chunks):
        start = index * step
        end = start + MAX_CHUNK_WORDS
        chunk_words = words[start:end]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
    return chunks
