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
]

SOURCE_PRIORITIES = [priority.value for priority in SourcePriority]
VERIFICATION_STATES = [state.value for state in VerificationState]
SUPPORTED_LANGUAGES = ["es-ES", "en-US"]
