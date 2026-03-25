from __future__ import annotations

import math
import re
from typing import Iterable

from realtime_phone_agents.knowledge.intent_router import extract_room_type_id
from realtime_phone_agents.knowledge.models import (
    HotelKnowledgeBundle,
    KnowledgeEntry,
    SourcePriority,
    VerificationState,
)


MAX_CHUNK_WORDS = 600
CHUNK_OVERLAP_WORDS = 80


def normalize_knowledge_bundle(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    entries.extend(_normalize_property_entries(bundle))
    entries.extend(_normalize_service_entries(bundle))
    entries.extend(_normalize_policy_entries(bundle))
    entries.extend(_normalize_room_type_entries(bundle))
    entries.extend(_normalize_pricing_entries(bundle))
    entries.extend(_normalize_document_entries(bundle))
    entries.extend(_normalize_faq_entries(bundle))
    return entries


def _normalize_property_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    hotel = bundle.hotel
    contact = hotel.property.contact
    return [
        KnowledgeEntry(
            id="overview_property",
            title=hotel.property.name,
            body=(
                f"{hotel.property.name} es un alojamiento boutique en un antiguo barrio de pescadores, "
                f"cerca del mar y al inicio del casco historico de Altea. "
                f"Direccion: {hotel.property.address_public}."
            ),
            entity_type="overview",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/"],
            tags=["overview", "location", "boutique"],
        ),
        KnowledgeEntry(
            id="location_address",
            title="Ubicacion y direccion",
            body=(
                f"El alojamiento esta en {hotel.property.address_public}, cerca del mar y del casco historico de Altea."
            ),
            entity_type="location",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/"],
            tags=["location", "address"],
        ),
        KnowledgeEntry(
            id="contact_primary",
            title="Contacto del alojamiento",
            body=(
                f"Telefono de contacto: {contact.phone}. Email: {contact.email}. "
                "Si falta un dato confirmado, se recomienda confirmar por telefono o email."
            ),
            entity_type="contact",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/"],
            tags=["contact"],
        ),
        KnowledgeEntry(
            id="parking_public_free",
            title="Parking publico gratuito",
            body=(
                "No hay parking dentro del alojamiento. Hay parking publico gratuito a unos "
                f"{hotel.parking.public_free_parking.walking_distance_m} metros andando. "
                f"Referencia: {hotel.parking.public_free_parking.location_note}. "
                f"Nota: {hotel.parking.public_free_parking.liability_note}."
            ),
            entity_type="parking",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=[
                "https://bluesardinealtea.com/",
                "https://bluesardinealtea.com/en/general-conditions/",
            ],
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
            tokens=services.experience,
            bundle=bundle,
            tags=["services", "experience"],
        ),
        _entry_from_token_list(
            entry_id="service_housekeeping",
            title="Limpieza y confort",
            body_prefix="Limpieza y confort",
            entity_type="service",
            tokens=services.housekeeping,
            bundle=bundle,
            tags=["services", "housekeeping"],
        ),
        _entry_from_token_list(
            entry_id="service_facilities",
            title="Equipamiento general",
            body_prefix="Equipamiento general",
            entity_type="service",
            tokens=services.in_room_and_property,
            bundle=bundle,
            tags=["services", "facilities"],
        ),
    ]


def _normalize_policy_entries(bundle: HotelKnowledgeBundle) -> list[KnowledgeEntry]:
    policies = bundle.hotel.policies
    return [
        KnowledgeEntry(
            id="policy_checkin_checkout",
            title="Check-in y check-out",
            body=(
                f"El check-in es a partir de las {policies.check_in} y el check-out debe hacerse antes de las "
                f"{policies.check_out}."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "checkin", "checkout"],
        ),
        KnowledgeEntry(
            id="policy_luggage",
            title="Consigna y salida",
            body=(
                "Hay taquillas gratuitas para equipaje y un sistema de buzon para dejar las llaves a la salida."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "luggage"],
        ),
        KnowledgeEntry(
            id="policy_adults_children",
            title="Politica de adultos y menores",
            body=(
                "El alojamiento esta orientado a adultos y admite ninos a partir de "
                f"{policies.adults_and_children.children_allowed_from_age} anos."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "adults", "children"],
        ),
        KnowledgeEntry(
            id="policy_smoke_free",
            title="Politica de humo",
            body="El establecimiento es smoke-free y fumar puede conllevar cargos.",
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "smoking"],
        ),
        KnowledgeEntry(
            id="policy_pets",
            title="Mascotas",
            body="No se permiten mascotas.",
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "pets"],
        ),
        KnowledgeEntry(
            id="policy_bicycles_scooters",
            title="Bicicletas y patinetes",
            body="No se permiten bicicletas ni patinetes electricos dentro del alojamiento ni en las habitaciones.",
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "bicycles", "scooters"],
        ),
        KnowledgeEntry(
            id="policy_reservation_hours",
            title="Horario de reservas",
            body=(
                f"Atencion telefonica: {policies.reservation_hours.phone_support}. "
                f"Reservas web: {policies.reservation_hours.website_booking}."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "reservations"],
        ),
        KnowledgeEntry(
            id="policy_payment_cancellation",
            title="Pago y cancelacion",
            body=(
                "Se requiere tarjeta valida. La cancelacion gratuita aplica hasta 5 dias antes de la llegada. "
                "No se permiten cambios de fecha dentro de los 5 dias previos. "
                "En tarifa no reembolsable no se permiten cancelaciones ni modificaciones. "
                "La fuerza mayor queda sujeta a revision del equipo de reservas."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
            tags=["policy", "payment", "cancellation"],
        ),
        KnowledgeEntry(
            id="policy_damages",
            title="Cargos por danos y perdidas",
            body=(
                "Se aplican cargos por danos y perdidas. Toalla pequena: 10 EUR. "
                "Toalla grande: 15 EUR. Los elementos decorativos se cobran segun su valor."
            ),
            entity_type="policy",
            language="es-ES",
            source_priority=SourcePriority.OFFICIAL,
            verification_state=VerificationState.OFFICIAL,
            version=bundle.manifest.kb_version,
            sources=["https://bluesardinealtea.com/en/general-conditions/"],
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
            KnowledgeEntry(
                id=f"room_type_{room_type.id}",
                title=room_type.display_name_es,
                body=". ".join(details) + ".",
                entity_type="room_type",
                room_type_id=room_type.id,
                language="es-ES",
                source_priority=SourcePriority.OFFICIAL,
                verification_state=VerificationState.OFFICIAL,
                area_sqm=room_type.area_sqm or 0,
                adults_max=room_type.occupancy.adults_max,
                version=bundle.manifest.kb_version,
                sources=["https://bluesardinealtea.com/"],
                tags=["room_type", room_type.id],
            )
        )

    for extension in bundle.room_types.room_type_extensions:
        entries.append(
            KnowledgeEntry(
                id=f"room_type_extension_{extension.id}",
                title=extension.display_name_es,
                body=(
                    f"{extension.display_name_es} aparece en canales externos, pero no esta descrita con detalle en la web principal. "
                    f"Nota: {extension.notes}"
                ),
                entity_type="room_type",
                room_type_id=extension.id,
                language="es-ES",
                source_priority=SourcePriority.THIRD_PARTY,
                verification_state=VerificationState.THIRD_PARTY,
                version=bundle.manifest.kb_version,
                sources=["https://www.google.com/travel/hotels"],
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
        KnowledgeEntry(
            id="pricing_summary",
            title="Precios orientativos e inventario interno",
            body=(
                "Los precios base internos son orientativos, pueden variar por temporada y ocupacion, "
                "y requieren confirmacion final. La configuracion interna actual suma "
                f"{pricing.inventory_sum_units} unidades y mantiene una discrepancia interna de "
                f"{pricing.inventory_gap_units} unidad frente a una pista externa de 21."
            ),
            entity_type="pricing",
            language="es-ES",
            source_priority=SourcePriority.INTERNAL_UNVALIDATED,
            verification_state=VerificationState.INTERNAL_UNVALIDATED,
            version=bundle.manifest.kb_version,
            sources=["internal://pricing_inventory_internal"],
            tags=["pricing", "inventory"],
        )
    ]

    for item in pricing.inventory_breakdown:
        entries.append(
            KnowledgeEntry(
                id=f"pricing_{item.room_type_id}",
                title=f"Precio orientativo {room_display_names[item.room_type_id]}",
                body=(
                    f"Precio base interno orientativo desde {item.base_price_eur} EUR para {room_display_names[item.room_type_id]}. "
                    f"Configuracion actual: {item.units} unidades. Dato interno pendiente de validacion y sujeto a temporada y ocupacion."
                ),
                entity_type="pricing",
                room_type_id=item.room_type_id,
                language="es-ES",
                source_priority=SourcePriority.INTERNAL_UNVALIDATED,
                verification_state=VerificationState.INTERNAL_UNVALIDATED,
                base_price_eur=item.base_price_eur,
                version=bundle.manifest.kb_version,
                sources=["internal://pricing_inventory_internal"],
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
            entries.append(
                KnowledgeEntry(
                    id=f"document_{document.doc_id}{chunk_suffix}",
                    title=document.title,
                    body=chunk,
                    entity_type=entity_type,
                    room_type_id=extract_room_type_id(
                        document.title + " " + document.body
                    ),
                    language=document.language,
                    source_priority=document.metadata.source_priority,
                    verification_state=_priority_to_verification(
                        document.metadata.source_priority
                    ),
                    version=bundle.manifest.kb_version,
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
        entries.append(
            KnowledgeEntry(
                id=f"faq_{index}",
                title=item.q,
                body=item.a,
                entity_type=entity_type,
                room_type_id=extract_room_type_id(combined_text),
                language="es-ES",
                source_priority=SourcePriority.OFFICIAL,
                verification_state=VerificationState.OFFICIAL,
                version=bundle.manifest.kb_version,
                sources=item.sources,
                tags=["faq", entity_type],
            )
        )
    return entries


def _entry_from_token_list(
    entry_id: str,
    title: str,
    body_prefix: str,
    entity_type: str,
    tokens: Iterable[str],
    bundle: HotelKnowledgeBundle,
    tags: list[str],
) -> KnowledgeEntry:
    body = (
        body_prefix + ": " + ", ".join(_humanize_token(token) for token in tokens) + "."
    )
    return KnowledgeEntry(
        id=entry_id,
        title=title,
        body=body,
        entity_type=entity_type,
        language="es-ES",
        source_priority=SourcePriority.OFFICIAL,
        verification_state=VerificationState.OFFICIAL,
        version=bundle.manifest.kb_version,
        sources=["https://bluesardinealtea.com/"],
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
