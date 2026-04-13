import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from realtime_phone_agents.api.routes.health import health_check


def load_script_module(relative_path: str, module_name: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DeploymentValidationTests(unittest.TestCase):
    def test_validate_env_accepts_primary_configuration(self):
        module = load_script_module(
            "scripts/validate_deployment_env.py",
            "validate_deployment_env_under_test",
        )
        fake_settings = SimpleNamespace(
            runpod=SimpleNamespace(
                api_key="runpod-key",
                call_center_image_name="hotel-agent:latest",
                call_center_instance_id="cpu5c-2-4",
            ),
            groq=SimpleNamespace(api_key="groq-key", model="openai/gpt-oss-20b"),
            mistral=SimpleNamespace(
                api_key="mistral-key",
                voice_id="voice-all",
                voice_id_en="",
                voice_id_es="",
            ),
            server=SimpleNamespace(public_base_url="https://hotel.example"),
            openai=SimpleNamespace(api_key="openai-key"),
            qdrant=SimpleNamespace(host="qdrant.example", port=6333),
            knowledge_base=SimpleNamespace(
                default_bundle_path="data/blue_sardine_kb/2026-04-11",
                collection_name="hotel-knowledge",
                default_hotel_id="blue_sardine_altea",
                auto_ingest_default_bundle=False,
            ),
            twilio=SimpleNamespace(account_sid="sid", auth_token="token"),
            stt_model="whisper-groq",
            tts_model="mistral-voxtral",
        )

        with patch.object(module, "settings", fake_settings):
            errors = module._validate_required_fields(include_outbound=True)

        self.assertEqual(errors, [])

    def test_validate_env_flags_wrong_primary_provider_defaults(self):
        module = load_script_module(
            "scripts/validate_deployment_env.py",
            "validate_deployment_env_wrong_defaults",
        )
        fake_settings = SimpleNamespace(
            runpod=SimpleNamespace(
                api_key="runpod-key",
                call_center_image_name="hotel-agent:latest",
                call_center_instance_id="cpu5c-2-4",
            ),
            groq=SimpleNamespace(api_key="groq-key", model="openai/gpt-oss-20b"),
            mistral=SimpleNamespace(
                api_key="mistral-key",
                voice_id="voice-all",
                voice_id_en="",
                voice_id_es="",
            ),
            server=SimpleNamespace(public_base_url="https://hotel.example"),
            openai=SimpleNamespace(api_key="openai-key"),
            qdrant=SimpleNamespace(host="qdrant.example", port=6333),
            knowledge_base=SimpleNamespace(
                default_bundle_path="data/blue_sardine_kb/2026-04-11",
                collection_name="hotel-knowledge",
                default_hotel_id="blue_sardine_altea",
                auto_ingest_default_bundle=False,
            ),
            twilio=SimpleNamespace(account_sid="sid", auth_token="token"),
            stt_model="faster-whisper",
            tts_model="together",
        )

        with patch.object(module, "settings", fake_settings):
            errors = module._validate_required_fields(include_outbound=False)

        self.assertTrue(any("STT_MODEL" in error for error in errors))
        self.assertTrue(any("TTS_MODEL" in error for error in errors))


class OutboundCallScriptTests(unittest.TestCase):
    def test_outbound_call_uses_public_telephone_entrypoint(self):
        module = load_script_module(
            "scripts/make_outbound_call.py",
            "make_outbound_call_under_test",
        )

        self.assertEqual(
            module.build_twilio_call_url("https://hotel.example"),
            "https://hotel.example/voice/telephone/incoming",
        )


class HealthRouteTests(unittest.TestCase):
    def test_health_route_returns_503_when_voice_mount_failed(self):
        app = FastAPI()
        app.state.voice_stream_available = False
        app.state.voice_stream_error = "boom"
        app.state.knowledge_service = object()
        app.add_api_route("/health", health_check, methods=["GET"])

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["voice_stream_error"], "boom")

    def test_health_route_returns_200_when_voice_and_knowledge_are_ready(self):
        app = FastAPI()
        app.state.voice_stream_available = True
        app.state.voice_stream_error = None
        app.state.knowledge_service = object()
        app.add_api_route("/health", health_check, methods=["GET"])

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
