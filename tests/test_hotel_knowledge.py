import json
import shutil
import tempfile
import unittest
from pathlib import Path

from realtime_phone_agents.infrastructure.superlinked.service import (
    KnowledgeSearchService,
)
from realtime_phone_agents.knowledge.intent_router import (
    detect_amenity_type,
    detect_intent,
    detect_policy_type,
    extract_room_type_id,
)
from realtime_phone_agents.knowledge.loader import load_knowledge_bundle, sha256_file
from realtime_phone_agents.knowledge.models import Intent
from realtime_phone_agents.knowledge.normalization import normalize_knowledge_bundle


BUNDLE_PATH = Path("data/blue_sardine_kb/2026-04-11")


class LoaderTests(unittest.TestCase):
    def test_load_bundle_and_validate_inventory(self):
        bundle = load_knowledge_bundle(BUNDLE_PATH)
        self.assertEqual(bundle.manifest.kb_version, "2026-04-11")
        self.assertEqual(
            bundle.pricing_inventory.pricing_and_inventory_internal.inventory_gap_units,
            1,
        )
        self.assertIn("standard_room", bundle.all_room_type_ids)
        self.assertIn("double_economic", bundle.all_room_type_ids)
        self.assertEqual(len(bundle.dialogues.dialogues), 8)
        self.assertEqual(len(bundle.operational_notes.notes), 6)

    def test_loader_detects_manifest_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "2026-04-11"
            shutil.copytree(BUNDLE_PATH, target)
            manifest_path = target / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["hotel.json"] = "deadbeef"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_knowledge_bundle(target)

    def test_loader_detects_unknown_room_type_reference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "2026-04-11"
            shutil.copytree(BUNDLE_PATH, target)
            pricing_path = target / "pricing_inventory_internal.json"
            pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
            pricing["pricing_and_inventory_internal"]["inventory_breakdown"][0][
                "room_type_id"
            ] = "unknown_room"
            pricing_path.write_text(json.dumps(pricing, indent=2), encoding="utf-8")

            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            manifest["files"]["pricing_inventory_internal.json"] = sha256_file(
                pricing_path
            )
            (target / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )

            with self.assertRaises(ValueError):
                load_knowledge_bundle(target)


class NormalizationTests(unittest.TestCase):
    def test_normalization_generates_expected_entry_types(self):
        bundle = load_knowledge_bundle(BUNDLE_PATH)
        entries = normalize_knowledge_bundle(bundle)
        ids = {entry.id for entry in entries}
        self.assertIn("overview_property", ids)
        self.assertIn("policy_pets", ids)
        self.assertIn("pricing_standard_room", ids)
        self.assertIn("dialogue_D09", ids)
        self.assertIn("operational_note_address_conflict", ids)
        self.assertTrue(
            any(entry.doc_type == "faq" and entry.faq_id == "faq_parking" for entry in entries)
        )
        self.assertTrue(
            any(
                entry.id == "pricing_standard_room"
                and entry.verification_state.value == "internal_unvalidated"
                for entry in entries
            )
        )
        self.assertTrue(
            any(
                entry.id == "dialogue_D16"
                and entry.doc_type == "dialogue_exemplar"
                and entry.requires_handoff
                for entry in entries
            )
        )


class IntentRouterTests(unittest.TestCase):
    def test_detect_intents(self):
        self.assertEqual(detect_intent("Se admiten mascotas?"), Intent.POLICIES)
        self.assertEqual(
            detect_intent("Hay parking gratis?"), Intent.LOCATION_AND_PARKING
        )
        self.assertEqual(
            detect_intent("How much is the studio with terrace?"),
            Intent.AVAILABILITY_PRICING,
        )
        self.assertEqual(
            detect_intent("Quiero una habitacion con terraza"),
            Intent.ROOM_SELECTION,
        )

    def test_extract_room_type_id(self):
        self.assertEqual(
            extract_room_type_id("Quiero informacion del apartamento Sardine"),
            "sardine_apartment",
        )
        self.assertEqual(
            extract_room_type_id("Tell me about the budget double room"),
            "double_economic",
        )

    def test_detect_policy_and_amenity_types(self):
        self.assertEqual(detect_policy_type("Aceptais Visa?"), "payment")
        self.assertEqual(detect_policy_type("Se puede fumar?"), "smoking")
        self.assertEqual(detect_amenity_type("El desayuno esta incluido?"), "breakfast")
        self.assertEqual(detect_amenity_type("Hay parking gratis?"), "parking")


class KnowledgeSearchServiceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = KnowledgeSearchService(
            None, None, None, None, force_in_memory=True
        )
        cls.service.ingest_knowledge_bundle(BUNDLE_PATH)

    async def test_policy_search_for_pets(self):
        response = await self.service.search_knowledge("Se admiten mascotas?", limit=3)
        self.assertEqual(response["resolved_intent"], Intent.POLICIES.value)
        self.assertGreaterEqual(response["result_count"], 1)
        self.assertTrue(
            any("mascotas" in item["body"].lower() for item in response["results"])
        )

    async def test_checkin_checkout_search(self):
        response = await self.service.search_knowledge(
            "A que hora es el check-in y el check-out?", limit=3
        )
        bodies = " ".join(item["body"] for item in response["results"])
        self.assertIn("15:00", bodies)
        self.assertIn("12:00", bodies)

    async def test_parking_search_returns_operational_note(self):
        response = await self.service.search_knowledge("Hay parking?", limit=3)
        self.assertEqual(response["resolved_intent"], Intent.LOCATION_AND_PARKING.value)
        bodies = " ".join(item["body"] for item in response["results"])
        self.assertIn("200 metros", bodies)
        self.assertIn("Calle La Mar 98", bodies)

    async def test_room_selection_returns_standard_room_details(self):
        response = await self.service.search_knowledge(
            "Describe la Habitacion Doble Estandar", limit=3
        )
        self.assertEqual(response["resolved_intent"], Intent.ROOM_SELECTION.value)
        self.assertTrue(
            any(
                item["room_type_id"] == "standard_room" and "15 m2" in item["body"]
                for item in response["results"]
            )
        )

    async def test_pricing_guardrail_requires_dates(self):
        response = await self.service.search_knowledge(
            "How much is the studio with terrace?", limit=3
        )
        self.assertEqual(response["resolved_intent"], Intent.AVAILABILITY_PRICING.value)
        self.assertTrue(
            any("Pide fechas exactas" in note for note in response["guardrail_notes"])
        )
        self.assertTrue(
            any(
                item["room_type_id"] == "studio_with_terrace"
                and item["verification_state"] == "internal_unvalidated"
                for item in response["results"]
            )
        )

    async def test_nearby_area_retrieval(self):
        response = await self.service.search_knowledge(
            "Que hay para visitar por ahi?", limit=3
        )
        bodies = " ".join(item["body"] for item in response["results"])
        self.assertIn("casco antiguo", bodies.lower())
        self.assertIn("kayak", bodies.lower())

    async def test_breakfast_unknown_marks_requires_handoff(self):
        response = await self.service.search_knowledge(
            "El desayuno esta incluido?", limit=3
        )
        self.assertTrue(any(item["requires_handoff"] for item in response["results"]))
        self.assertTrue(
            any("no se menciona desayuno" in item["body"].lower() for item in response["results"])
        )

    async def test_accessibility_unknown_marks_requires_handoff(self):
        response = await self.service.search_knowledge(
            "Teneis habitaciones adaptadas o acceso para silla de ruedas?", limit=3
        )
        self.assertTrue(any(item["requires_handoff"] for item in response["results"]))
        self.assertTrue(
            any("accesibilidad" in item["body"].lower() for item in response["results"])
        )

    async def test_address_conflict_retrieval_surfaces_handoff(self):
        response = await self.service.search_knowledge(
            "Necesito la direccion exacta para un taxi", limit=3
        )
        bodies = " ".join(item["body"] for item in response["results"])
        self.assertIn("Calle Pescadores 1", bodies)
        self.assertIn("Calle La Mar 54", bodies)
        self.assertTrue(any(item["requires_handoff"] for item in response["results"]))

    async def test_style_mode_returns_only_dialogues(self):
        response = await self.service.search_knowledge(
            "Como responderias a una duda de desayuno?",
            limit=2,
            search_mode="style",
        )
        self.assertTrue(response["results"])
        self.assertTrue(
            all(item["doc_type"] == "dialogue_exemplar" for item in response["results"])
        )


if __name__ == "__main__":
    unittest.main()
