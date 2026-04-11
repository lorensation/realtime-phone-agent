from realtime_phone_agents.knowledge.models import SourcePriority, VerificationState


ENTITY_TYPES = [
    "overview",
    "location",
    "contact",
    "parking",
    "service",
    "policy",
    "room_type",
    "pricing",
    "dialogue",
    "operational_note",
]

SOURCE_PRIORITIES = [priority.value for priority in SourcePriority]
VERIFICATION_STATES = [state.value for state in VerificationState]
SUPPORTED_LANGUAGES = ["es-ES", "en-US"]
DOC_TYPES = [
    "structured_fact",
    "policy_fact",
    "room_fact",
    "document",
    "faq",
    "dialogue_exemplar",
    "operational_note",
]
SECTIONS = [
    "overview",
    "location",
    "contact",
    "parking",
    "services",
    "policies",
    "rooms",
    "pricing",
    "operations",
]
HOTEL_IDS = ["blue_sardine_altea"]
POLICY_TYPES = [
    "checkin",
    "checkout",
    "pets",
    "children",
    "smoking",
    "luggage",
    "cancellation",
    "payment",
    "mobility",
    "reservation_hours",
    "damages",
]
AMENITY_TYPES = [
    "parking",
    "guest_experience",
    "housekeeping",
    "facilities",
    "wifi",
    "breakfast",
    "kitchen",
    "laundry",
    "television",
    "air_conditioning",
    "accessibility",
]
