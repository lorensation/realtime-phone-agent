from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from realtime_phone_agents.knowledge.models import (
    DocumentsData,
    FAQData,
    HotelData,
    HotelKnowledgeBundle,
    Manifest,
    PricingInventoryData,
    RoomTypesData,
)


REQUIRED_BUNDLE_FILES = (
    "hotel.json",
    "room_types.json",
    "pricing_inventory_internal.json",
    "faq.json",
    "documents.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def load_knowledge_bundle(bundle_path: str | Path) -> HotelKnowledgeBundle:
    base_path = Path(bundle_path)
    if not base_path.exists():
        raise FileNotFoundError(f"Knowledge bundle path does not exist: {base_path}")
    if not base_path.is_dir():
        raise NotADirectoryError(f"Knowledge bundle path must be a directory: {base_path}")

    manifest_path = base_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Knowledge bundle manifest is missing: {manifest_path}")

    try:
        manifest = Manifest.model_validate(_load_json(manifest_path))
        hotel = HotelData.model_validate(_load_json(base_path / "hotel.json"))
        room_types = RoomTypesData.model_validate(_load_json(base_path / "room_types.json"))
        pricing_inventory = PricingInventoryData.model_validate(
            _load_json(base_path / "pricing_inventory_internal.json")
        )
        faq = FAQData.model_validate(_load_json(base_path / "faq.json"))
        documents = DocumentsData.model_validate(_load_json(base_path / "documents.json"))
    except ValidationError as exc:
        raise ValueError(f"Invalid knowledge bundle data in {base_path}: {exc}") from exc

    missing_files = [filename for filename in REQUIRED_BUNDLE_FILES if not (base_path / filename).exists()]
    if missing_files:
        raise FileNotFoundError(
            f"Knowledge bundle is missing required files: {', '.join(sorted(missing_files))}"
        )

    expected_manifest_files = set(REQUIRED_BUNDLE_FILES)
    if set(manifest.files.keys()) != expected_manifest_files:
        raise ValueError(
            "manifest.json files section must contain exactly: "
            + ", ".join(sorted(expected_manifest_files))
        )

    for filename, expected_checksum in manifest.files.items():
        actual_checksum = sha256_file(base_path / filename)
        if actual_checksum != expected_checksum:
            raise ValueError(
                f"Checksum mismatch for {filename}: expected {expected_checksum}, got {actual_checksum}"
            )

    return HotelKnowledgeBundle(
        manifest=manifest,
        hotel=hotel,
        room_types=room_types,
        pricing_inventory=pricing_inventory,
        faq=faq,
        documents=documents,
        bundle_path=base_path,
    )
