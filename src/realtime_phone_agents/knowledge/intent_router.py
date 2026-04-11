from __future__ import annotations

import re
import unicodedata

from realtime_phone_agents.knowledge.models import Intent


ROOM_TYPE_ALIASES = {
    "standard_room": [
        "standard room",
        "habitacion estandar",
        "habitacion doble estandar",
        "doble estandar",
        "standard",
    ],
    "superior_room": [
        "superior room",
        "habitacion superior",
        "habitacion doble superior",
        "doble superior",
        "superior",
    ],
    "premium_room": [
        "premium room",
        "habitacion premium",
        "habitacion con terraza",
        "doble con terraza",
        "room with terrace",
        "premium",
    ],
    "studio_with_terrace": [
        "studio with terrace",
        "estudio con terraza",
        "studio room with terrace",
        "estudio",
    ],
    "blue_apartment": [
        "apartamento blue",
        "blue apartment",
        "blue 04",
        "apartamento blue 04",
    ],
    "sardine_apartment": [
        "apartamento sardine",
        "sardine apartment",
        "sardine 05",
        "apartamento sardine 05",
    ],
    "double_economic": [
        "habitacion doble economica",
        "doble economica",
        "economic double room",
        "budget double room",
        "economic room",
    ],
}

PRICING_KEYWORDS = {
    "precio",
    "precios",
    "tarifa",
    "tarifas",
    "coste",
    "costo",
    "cuanto",
    "cuanto cuesta",
    "price",
    "how much",
    "price of",
    "prices",
    "rate",
    "rates",
    "cost",
    "availability",
    "available",
    "disponible",
    "disponibilidad",
    "reservar",
    "book",
    "booking",
}

LOCATION_KEYWORDS = {
    "parking",
    "aparcamiento",
    "ubicacion",
    "localizacion",
    "direccion",
    "address",
    "where",
    "donde",
    "playa",
    "beach",
    "mar",
    "sea",
    "casco historico",
    "old town",
    "tren",
    "station",
}

SPECIAL_REQUEST_KEYWORDS = {
    "cumpleanos",
    "birthday",
    "anniversary",
    "aniversario",
    "celebracion",
    "celebration",
    "special request",
    "romantic",
}

POLICY_KEYWORDS = {
    "mascota",
    "mascotas",
    "pet",
    "pets",
    "fumar",
    "smoke",
    "smoking",
    "check in",
    "check-in",
    "check out",
    "check-out",
    "checkout",
    "cancel",
    "cancelacion",
    "reembolso",
    "refund",
    "policy",
    "politica",
    "politicas",
    "bici",
    "bicicleta",
    "patinete",
    "scooter",
    "luggage",
    "equipaje",
    "locker",
    "consigna",
    "adult",
    "children",
    "child",
    "nino",
    "ninos",
}

ROOM_KEYWORDS = {
    "habitacion",
    "habitaciones",
    "room",
    "rooms",
    "studio",
    "estudio",
    "apartment",
    "apartamento",
    "terraza",
    "terrace",
}

DATE_PATTERN = re.compile(
    r"(\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b|"
    r"\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|"
    r"january|february|march|april|may|june|july|august|september|october|november|december)\b)"
)
AREA_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:m2|m\^2|metros cuadrados|metros|sqm|square meters?)\b"
)
PRICE_PATTERN = re.compile(
    r"(?:€\s*(\d{2,4})|(\d{2,4})\s*€|(?:desde|from|under|menos de|hasta)\s*(\d{2,4}))"
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )


def build_room_type_aliases() -> dict[str, list[str]]:
    return ROOM_TYPE_ALIASES


def extract_room_type_id(query: str) -> str | None:
    normalized_query = normalize_text(query)
    for room_type_id, aliases in ROOM_TYPE_ALIASES.items():
        if any(alias in normalized_query for alias in aliases):
            return room_type_id
    return None


def detect_intent(query: str) -> Intent | None:
    normalized_query = normalize_text(query)
    if any(keyword in normalized_query for keyword in PRICING_KEYWORDS):
        return Intent.AVAILABILITY_PRICING
    if any(keyword in normalized_query for keyword in LOCATION_KEYWORDS):
        return Intent.LOCATION_AND_PARKING
    if any(keyword in normalized_query for keyword in SPECIAL_REQUEST_KEYWORDS):
        return Intent.SPECIAL_REQUESTS
    if any(keyword in normalized_query for keyword in POLICY_KEYWORDS):
        return Intent.POLICIES
    if extract_room_type_id(normalized_query) or any(
        keyword in normalized_query for keyword in ROOM_KEYWORDS
    ):
        return Intent.ROOM_SELECTION
    return None


def extract_area_sqm_hint(query: str) -> int | None:
    normalized_query = normalize_text(query)
    match = AREA_PATTERN.search(normalized_query)
    if not match:
        return None
    return int(match.group(1))


def extract_base_price_hint(query: str) -> int | None:
    normalized_query = normalize_text(query)
    match = PRICE_PATTERN.search(normalized_query)
    if not match:
        return None
    numbers = [group for group in match.groups() if group]
    return int(numbers[0]) if numbers else None


def has_explicit_stay_dates(query: str) -> bool:
    normalized_query = normalize_text(query)
    if DATE_PATTERN.search(normalized_query):
        return True
    relative_terms = {
        "hoy",
        "manana",
        "pasado manana",
        "next week",
        "next month",
        "tomorrow",
        "today",
        "this weekend",
        "este fin de semana",
    }
    return any(term in normalized_query for term in relative_terms)


def is_unverified_amenity_question(query: str) -> bool:
    normalized_query = normalize_text(query)
    amenity_terms = {
        "2 botellas de agua",
        "dos botellas de agua",
        "water bottles",
        "bottled water",
        "welcome water",
    }
    return any(term in normalized_query for term in amenity_terms)


def detect_policy_type(query: str) -> str | None:
    normalized_query = normalize_text(query)
    mapping = {
        "checkin": {"check in", "check-in", "checkin"},
        "checkout": {"check out", "check-out", "checkout"},
        "pets": {"mascota", "mascotas", "pet", "pets"},
        "children": {"nino", "ninos", "children", "child", "adult"},
        "smoking": {"fumar", "smoke", "smoking"},
        "luggage": {"equipaje", "locker", "luggage", "consigna"},
        "cancellation": {"cancel", "cancelacion", "refund", "reembolso"},
        "payment": {"payment", "pago", "tarjeta", "card", "visa", "mastercard"},
        "mobility": {"bici", "bicicleta", "patinete", "scooter"},
    }
    for policy_type, keywords in mapping.items():
        if any(keyword in normalized_query for keyword in keywords):
            return policy_type
    return None


def detect_amenity_type(query: str) -> str | None:
    normalized_query = normalize_text(query)
    mapping = {
        "parking": {"parking", "aparcamiento"},
        "wifi": {"wifi", "wi-fi", "internet"},
        "breakfast": {"desayuno", "breakfast"},
        "kitchen": {"cocina", "kitchen", "microondas", "microwave"},
        "laundry": {"lavadora", "laundry", "washing machine"},
        "television": {"tv", "television", "smart tv"},
        "air_conditioning": {
            "aire acondicionado",
            "climatizacion",
            "air conditioning",
        },
        "accessibility": {
            "accesible",
            "accessibility",
            "wheelchair",
            "silla de ruedas",
        },
    }
    for amenity_type, keywords in mapping.items():
        if any(keyword in normalized_query for keyword in keywords):
            return amenity_type
    return None
