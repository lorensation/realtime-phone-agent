from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourcePriority(str, Enum):
    OFFICIAL = "official"
    INTERNAL_VALIDATED = "internal_validated"
    INTERNAL_UNVALIDATED = "internal_unvalidated"
    THIRD_PARTY = "third_party"


class VerificationState(str, Enum):
    OFFICIAL = "official"
    INTERNAL_VALIDATED = "internal_validated"
    INTERNAL_UNVALIDATED = "internal_unvalidated"
    THIRD_PARTY = "third_party"


class Intent(str, Enum):
    ROOM_SELECTION = "room_selection"
    POLICIES = "policies"
    LOCATION_AND_PARKING = "location_and_parking"
    AVAILABILITY_PRICING = "availability_pricing"
    SPECIAL_REQUESTS = "special_requests"


class Manifest(StrictModel):
    kb_version: str
    generated_at: str
    property_name: str
    primary_domain: str
    responsible: str
    confidence: str
    files: dict[str, str]


class Source(StrictModel):
    primary_domain: str
    retrieved_local_date: str
    notes: str


class Contact(StrictModel):
    phone: str
    email: str


class Positioning(StrictModel):
    summary: str
    themes: list[str] = Field(default_factory=list)


class PropertyProfile(StrictModel):
    name: str
    category: str
    city: str
    region: str
    country: str
    address_public: str
    contact: Contact
    positioning: Positioning


class LuggageStorage(StrictModel):
    lockers_free: bool
    key_drop_mailbox: bool


class AdultsAndChildren(StrictModel):
    adults_only: bool
    children_allowed_from_age: int


class DamagesFeesEur(StrictModel):
    towel_small: int
    towel_large: int
    decor_items: str


class ReservationHours(StrictModel):
    phone_support: str
    website_booking: str


class NonRefundablePolicy(StrictModel):
    cancellation_allowed: bool
    date_modification_allowed: bool


class PaymentAndCancellation(StrictModel):
    card_required: bool
    payment_deadline_days_before_arrival: int
    free_cancellation_until_days_before_arrival: int
    date_changes_allowed_within_days_before_arrival: bool
    non_refundable: NonRefundablePolicy
    force_majeure: str


class Policies(StrictModel):
    check_in: str
    check_out: str
    luggage_storage: LuggageStorage
    adults_and_children: AdultsAndChildren
    smoke_free: bool
    pets_allowed: bool
    bicycles_and_scooters_allowed_inside: bool
    damages_fees_eur: DamagesFeesEur
    reservation_hours: ReservationHours
    payment_and_cancellation: PaymentAndCancellation


class PublicFreeParking(StrictModel):
    available: bool
    walking_distance_m: int
    location_note: str
    liability_note: str


class Parking(StrictModel):
    available_on_site: bool
    public_free_parking: PublicFreeParking


class ServicesAndFacilities(StrictModel):
    experience: list[str] = Field(default_factory=list)
    housekeeping: list[str] = Field(default_factory=list)
    in_room_and_property: list[str] = Field(default_factory=list)


class HotelData(StrictModel):
    kb_version: str
    source: Source
    property: PropertyProfile
    policies: Policies
    parking: Parking
    services_and_facilities: ServicesAndFacilities


class Occupancy(StrictModel):
    adults_max: int


class RoomType(StrictModel):
    id: str
    display_name_es: str
    occupancy: Occupancy
    bed: str
    area_sqm: int | None = None
    highlights: list[str] = Field(default_factory=list)
    layout: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)


class RoomTypeExtension(StrictModel):
    id: str
    display_name_es: str
    source: str
    notes: str
    needs_internal_validation: bool


class RoomTypesData(StrictModel):
    room_types: list[RoomType]
    room_type_extensions: list[RoomTypeExtension] = Field(default_factory=list)


class InventoryBreakdownItem(StrictModel):
    room_type_id: str
    units: int
    base_price_eur: int


class SeasonDefinition(StrictModel):
    season_id: str
    date_ranges: list[dict[str, str] | str] = Field(default_factory=list)
    price_multiplier: float


class PricingAndInventoryInternal(StrictModel):
    currency: str
    pricing_model: str
    status: str
    inventory_breakdown: list[InventoryBreakdownItem]
    inventory_sum_units: int
    inventory_expected_units_external_hint: int
    inventory_gap_units: int
    season_definitions_placeholder: list[SeasonDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_inventory_math(self) -> "PricingAndInventoryInternal":
        computed_sum = sum(item.units for item in self.inventory_breakdown)
        computed_gap = self.inventory_expected_units_external_hint - computed_sum
        if computed_sum != self.inventory_sum_units:
            raise ValueError(
                "inventory_sum_units does not match the units declared in inventory_breakdown"
            )
        if computed_gap != self.inventory_gap_units:
            raise ValueError(
                "inventory_gap_units does not match inventory_expected_units_external_hint - inventory_sum_units"
            )
        return self


class PricingInventoryData(StrictModel):
    pricing_and_inventory_internal: PricingAndInventoryInternal


class DocumentMetadata(StrictModel):
    source_priority: SourcePriority
    source_urls: list[str]
    source_type: str = "official_site"
    section: str | None = None
    doc_type: str = "document"
    tags: list[str] = Field(default_factory=list)


class Document(StrictModel):
    doc_id: str
    language: str
    title: str
    body: str
    metadata: DocumentMetadata


class DocumentsData(StrictModel):
    documents: list[Document]


class FAQItem(StrictModel):
    faq_id: str | None = None
    q: str
    a: str
    section: str | None = None
    policy_type: str | None = None
    amenity_type: str | None = None
    requires_handoff: bool = False
    sources: list[str] = Field(default_factory=list)


class FAQData(StrictModel):
    faq: list[FAQItem]


class DialogueExample(StrictModel):
    dialogue_id: str
    language: str = "es-ES"
    intent: str
    difficulty: str
    body: str
    requires_handoff: bool = False
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class DialoguesData(StrictModel):
    dialogues: list[DialogueExample]


class OperationalNote(StrictModel):
    note_id: str
    title: str
    body: str
    section: str
    confidence: str = "confirmed"
    requires_handoff: bool = False
    source_urls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OperationalNotesData(StrictModel):
    notes: list[OperationalNote]


class HotelKnowledgeBundle(StrictModel):
    manifest: Manifest
    hotel: HotelData
    room_types: RoomTypesData
    pricing_inventory: PricingInventoryData
    faq: FAQData
    documents: DocumentsData
    dialogues: DialoguesData
    operational_notes: OperationalNotesData
    bundle_path: Path | None = Field(default=None, exclude=True)

    @property
    def all_room_type_ids(self) -> set[str]:
        canonical_ids = {room_type.id for room_type in self.room_types.room_types}
        extension_ids = {
            room_type.id for room_type in self.room_types.room_type_extensions
        }
        return canonical_ids | extension_ids

    @property
    def contact(self) -> Contact:
        return self.hotel.property.contact

    @property
    def supported_languages(self) -> set[str]:
        languages = {document.language for document in self.documents.documents}
        languages |= {dialogue.language for dialogue in self.dialogues.dialogues}
        return languages | {"es-ES"}

    @model_validator(mode="after")
    def validate_bundle_consistency(self) -> "HotelKnowledgeBundle":
        if self.bundle_path and self.bundle_path.name != self.manifest.kb_version:
            raise ValueError("Bundle directory name must match manifest.kb_version")
        if self.hotel.kb_version != self.manifest.kb_version:
            raise ValueError("hotel.kb_version must match manifest.kb_version")
        if self.hotel.source.primary_domain != self.manifest.primary_domain:
            raise ValueError(
                "manifest.primary_domain must match hotel.source.primary_domain"
            )

        room_type_ids = [room_type.id for room_type in self.room_types.room_types]
        extension_ids = [
            room_type.id for room_type in self.room_types.room_type_extensions
        ]
        all_ids = room_type_ids + extension_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError(
                "Room type ids must be unique across canonical and extension room types"
            )

        unknown_room_type_ids = {
            item.room_type_id
            for item in self.pricing_inventory.pricing_and_inventory_internal.inventory_breakdown
            if item.room_type_id not in self.all_room_type_ids
        }
        if unknown_room_type_ids:
            raise ValueError(
                f"pricing_and_inventory_internal references unknown room_type_id values: {sorted(unknown_room_type_ids)}"
            )
        return self


class KnowledgeEntry(StrictModel):
    id: str
    title: str
    body: str
    entity_type: str
    hotel_id: str
    hotel_name: str
    brand_name: str
    source_url: str
    source_type: str
    section: str
    doc_type: str
    room_type: str | None = None
    amenity_type: str | None = None
    policy_type: str | None = None
    faq_id: str | None = None
    dialogue_id: str | None = None
    confidence: str
    requires_handoff: bool = False
    updated_at: str
    room_type_id: str | None = None
    language: str = "es-ES"
    source_priority: SourcePriority
    verification_state: VerificationState
    area_sqm: int = Field(default=0, ge=0)
    adults_max: int = Field(default=0, ge=0)
    base_price_eur: int = Field(default=0, ge=0)
    version: str
    sources: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
