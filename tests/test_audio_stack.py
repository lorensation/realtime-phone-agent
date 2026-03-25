import asyncio
import importlib.util
import base64
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

import realtime_phone_agents.agent.fastrtc_agent as agent_module
from realtime_phone_agents.agent.fastrtc_agent import (
    DEFAULT_SYSTEM_PROMPT,
    FastRTCAgent,
    classify_language_selection,
)
from realtime_phone_agents.api.routes.voice import (
    _build_telephone_twiml,
    _replace_telephone_incoming_route,
)
from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.config import Settings
from realtime_phone_agents.stt.runpod.faster_whisper.model import FasterWhisperSTT
from realtime_phone_agents.stt.runpod.faster_whisper.options import (
    FasterWhisperSTTOptions,
)
from realtime_phone_agents.stt.utils import get_stt_model
from realtime_phone_agents.tts.runpod.orpheus.model import OrpheusTTSModel
from realtime_phone_agents.tts.runpod.orpheus.options import OrpheusTTSOptions
from realtime_phone_agents.tts.togetherai.model import TogetherTTSModel
from realtime_phone_agents.tts.togetherai.options import TogetherTTSOptions
from realtime_phone_agents.tts.utils import get_tts_model
from fastapi import FastAPI
from fastapi import Request as FastAPIRequest


def load_gradio_launcher_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_gradio_application.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_gradio_application_under_test", script_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_orpheus_pod_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "runpod"
        / "create_orpheus_pod.py"
    )
    spec = importlib.util.spec_from_file_location(
        "create_orpheus_pod_under_test", script_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def collect_audio(async_iterator):
    return [item async for item in async_iterator]


class SettingsParsingTests(unittest.TestCase):
    def test_settings_accept_audio_provider_configuration(self):
        settings = Settings(
            _env_file=None,
            stt_model="moonshine",
            tts_model="kokoro",
            faster_whisper={
                "api_url": "https://faster-whisper.example",
                "model": "Systran/faster-whisper-large-v3",
            },
            orpheus={
                "api_url": "https://orpheus.example",
                "model": "orpheus-3b-0.1-ft",
            },
            together={
                "api_key": "together-key",
                "voice": "tara",
            },
            runpod={
                "api_key": "runpod-key",
                "orpheus_gpu_type": "GPU-A",
                "orpheus_image_name": "orpheus-image",
            },
            call_flow={
                "language_selection_enabled": True,
                "selection_retry_limit": 3,
                "ringback_seconds": 1.5,
            },
            orpheus_spanish={
                "api_url": "https://orpheus-spanish.example",
                "voice": "Maria",
            },
        )

        self.assertEqual(settings.stt_model, "moonshine")
        self.assertEqual(settings.tts_model, "kokoro")
        self.assertEqual(
            settings.faster_whisper.api_url, "https://faster-whisper.example"
        )
        self.assertEqual(settings.orpheus.api_url, "https://orpheus.example")
        self.assertEqual(
            settings.orpheus_spanish.api_url, "https://orpheus-spanish.example"
        )
        self.assertEqual(settings.orpheus_spanish.voice, "Maria")
        self.assertEqual(settings.together.api_key, "together-key")
        self.assertEqual(settings.runpod.orpheus_gpu_type, "GPU-A")
        self.assertEqual(settings.runpod.orpheus_image_name, "orpheus-image")
        self.assertTrue(settings.call_flow.language_selection_enabled)
        self.assertEqual(settings.call_flow.selection_retry_limit, 3)


class STTFactoryTests(unittest.TestCase):
    def test_get_stt_model_selects_provider(self):
        with patch(
            "realtime_phone_agents.stt.utils.MoonshineSTT", return_value="moonshine"
        ):
            self.assertEqual(get_stt_model("moonshine"), "moonshine")
        with patch(
            "realtime_phone_agents.stt.utils.WhisperGroqSTT",
            return_value="whisper-groq",
        ):
            self.assertEqual(get_stt_model("whisper-groq"), "whisper-groq")
        with patch(
            "realtime_phone_agents.stt.utils.FasterWhisperSTT",
            return_value="faster-whisper",
        ):
            self.assertEqual(get_stt_model("faster-whisper"), "faster-whisper")

    def test_get_stt_model_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            get_stt_model("unknown-stt")


class TTSFactoryTests(unittest.TestCase):
    def test_get_tts_model_selects_provider(self):
        with patch(
            "realtime_phone_agents.tts.utils.KokoroTTSModel", return_value="kokoro"
        ):
            self.assertEqual(get_tts_model("kokoro"), "kokoro")

        orpheus_instance = MagicMock()
        with patch(
            "realtime_phone_agents.tts.utils.OrpheusTTSModel",
            return_value=orpheus_instance,
        ):
            self.assertIs(get_tts_model("orpheus-runpod"), orpheus_instance)
            orpheus_instance.tts_blocking.assert_called_once()

        with patch(
            "realtime_phone_agents.tts.utils.TogetherTTSModel",
            return_value="together",
        ):
            self.assertEqual(get_tts_model("together"), "together")

    def test_get_tts_model_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            get_tts_model("unknown-tts")


class GroqWhisperSTTTests(unittest.TestCase):
    def test_whisper_groq_uses_openai_compatible_client(self):
        import realtime_phone_agents.stt.groq.whisper as groq_whisper

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="transcribed text"
        )
        fake_settings = SimpleNamespace(
            groq=SimpleNamespace(
                api_key="groq-key",
                base_url="https://groq.example/openai/v1",
                stt_model="whisper-large-v3",
            )
        )

        with (
            patch.object(groq_whisper, "settings", fake_settings),
            patch.object(groq_whisper, "OpenAI", return_value=mock_client),
            patch.object(groq_whisper, "audio_to_bytes", return_value=b"audio-bytes"),
        ):
            model = groq_whisper.WhisperGroqSTT()
            transcription = model.stt(("ignored", np.zeros(1, dtype=np.int16)))

        self.assertEqual(transcription, "transcribed text")
        mock_client.audio.transcriptions.create.assert_called_once()


class FasterWhisperSTTTests(unittest.TestCase):
    def test_faster_whisper_uses_stubbed_openai_client(self):
        import realtime_phone_agents.stt.runpod.faster_whisper.model as faster_whisper

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="runpod text"
        )

        with (
            patch.object(faster_whisper, "OpenAI", return_value=mock_client),
            patch.object(faster_whisper, "audio_to_bytes", return_value=b"audio-bytes"),
        ):
            model = FasterWhisperSTT(
                FasterWhisperSTTOptions(
                    api_url="https://faster-whisper.example",
                    model="Systran/faster-whisper-large-v3",
                )
            )
            transcription = model.stt(("ignored", np.zeros(1, dtype=np.int16)))

        self.assertEqual(transcription, "runpod text")
        mock_client.audio.transcriptions.create.assert_called_once()

    def test_faster_whisper_requires_api_url(self):
        with self.assertRaises(ValueError):
            FasterWhisperSTT(FasterWhisperSTTOptions(api_url="", model="model"))


class TogetherTTSModelTests(unittest.TestCase):
    def test_together_streams_audio_from_httpx_client(self):
        import realtime_phone_agents.tts.togetherai.model as together_model

        class FakeResponse:
            headers = {"content-type": "audio/raw"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_bytes(self):
                yield b"\x01\x00\x02\x00"
                yield b"\x03\x00\x04\x00"

        class FakeClient:
            last_request = None

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def stream(self, method, url, json):
                FakeClient.last_request = (method, url, json)
                return FakeResponse()

        with patch.object(together_model.httpx, "Client", FakeClient):
            model = TogetherTTSModel(
                TogetherTTSOptions(
                    api_key="together-key",
                    api_url="https://api.together.example/v1",
                    model="canopylabs/orpheus-3b-0.1-ft",
                    voice="tara",
                    sample_rate=24000,
                )
            )
            chunks = list(model.stream_tts_sync("hello"))

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], 24000)
        self.assertEqual(
            FakeClient.last_request[1], "https://api.together.example/v1/audio/speech"
        )

    def test_together_decodes_sse_audio_deltas(self):
        import realtime_phone_agents.tts.togetherai.model as together_model

        pcm_bytes = b"\x01\x00\x02\x00\x03\x00\x04\x00"
        audio_delta = base64.b64encode(pcm_bytes).decode("utf-8")

        class FakeResponse:
            headers = {"content-type": "text/event-stream; charset=utf-8"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self):
                yield (
                    'data: {"type":"conversation.item.audio_output.delta","delta":"'
                    + audio_delta
                    + '"}'
                )
                yield ""
                yield "data: [DONE]"
                yield ""

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def stream(self, method, url, json):
                return FakeResponse()

        with patch.object(together_model.httpx, "Client", FakeClient):
            model = TogetherTTSModel(
                TogetherTTSOptions(
                    api_key="together-key",
                    api_url="https://api.together.example/v1",
                    model="canopylabs/orpheus-3b-0.1-ft",
                    voice="tara",
                    sample_rate=24000,
                )
            )
            chunks = list(model.stream_tts_sync("hello"))

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], 24000)
        np.testing.assert_array_equal(
            chunks[0][1],
            np.frombuffer(pcm_bytes, dtype=np.int16),
        )


class OrpheusTTSModelTests(unittest.TestCase):
    def test_orpheus_streams_audio_from_stubbed_endpoint(self):
        import realtime_phone_agents.tts.runpod.orpheus.model as orpheus_model

        class FakeResponse:
            def raise_for_status(self):
                return None

            def iter_lines(self):
                for index in range(28):
                    token_number = 11 + ((index % 7) * 4096)
                    payload = "data: " + json.dumps(
                        {"choices": [{"text": f"<custom_token_{token_number}>"}]}
                    )
                    yield payload.encode("utf-8")
                yield b"data: [DONE]"

        with (
            patch.object(
                orpheus_model.requests, "post", return_value=FakeResponse()
            ) as mock_post,
            patch.object(
                orpheus_model, "convert_to_audio", return_value=b"\x01\x00\x02\x00"
            ),
        ):
            model = OrpheusTTSModel(
                OrpheusTTSOptions(
                    api_url="https://orpheus.example",
                    model="orpheus-3b-0.1-ft",
                    voice="tara",
                    sample_rate=24000,
                )
            )
            chunks = list(model.stream_tts_sync("hello"))

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], 24000)
        mock_post.assert_called_once()

    def test_orpheus_requires_api_url(self):
        with self.assertRaises(ValueError):
            OrpheusTTSModel(OrpheusTTSOptions(api_url="", model="orpheus"))


class FakeTTSModel:
    def __init__(self, marker: int):
        self.marker = marker
        self.texts: list[str] = []

    async def stream_tts(self, text: str, **kwargs):
        self.texts.append(text)
        yield 16000, np.array([self.marker], dtype=np.int16)

    def tts(self, text: str, **kwargs):
        self.texts.append(text)
        return 16000, np.array([self.marker], dtype=np.int16)


class FakeEffect:
    def __init__(self, marker: int):
        self.marker = marker

    async def stream(self):
        yield 16000, np.array([self.marker], dtype=np.float32)


class LanguageSelectionTests(unittest.TestCase):
    def test_classifies_accented_and_unaccented_choices(self):
        self.assertEqual(classify_language_selection("Ingles"), "english")
        self.assertEqual(classify_language_selection("ingles, por favor"), "english")
        self.assertEqual(classify_language_selection("Espanol"), "spanish")
        self.assertEqual(classify_language_selection("espanol"), "spanish")
        self.assertEqual(classify_language_selection("castellano"), "spanish")
        self.assertIsNone(classify_language_selection("quiero informacion"))

    def _build_fake_settings(self, enabled: bool) -> SimpleNamespace:
        return SimpleNamespace(
            call_flow=SimpleNamespace(
                language_selection_enabled=enabled,
                selection_retry_limit=2,
                ringback_seconds=1.0,
            ),
            orpheus_spanish=SimpleNamespace(
                api_url="https://spanish.example",
                model="spanish-model",
                voice="Maria",
                temperature=0.6,
                top_p=0.9,
                max_tokens=1200,
                repetition_penalty=1.1,
                sample_rate=24000,
                debug=False,
            ),
            groq=SimpleNamespace(model="groq-model", api_key="groq-key"),
            stt_model="whisper-groq",
            tts_model="together",
        )

    def test_startup_flow_plays_ringback_then_bilingual_prompt(self):
        fake_settings = self._build_fake_settings(enabled=True)
        english_tts = FakeTTSModel(2)
        spanish_tts = FakeTTSModel(3)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-1"),
            ),
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=english_tts,
                voice_effect=FakeEffect(9),
                ringback_effect=FakeEffect(1),
                spanish_tts_model=spanish_tts,
                tools=[search_hotel_kb_tool],
            )

            chunks = asyncio.run(collect_audio(agent._startup_prompt()))

        self.assertEqual([int(chunk[1][0]) for chunk in chunks], [1, 2, 3])
        self.assertEqual(
            english_tts.texts,
            [
                "Thank you for calling Blue Sardine Altea. "
                "If you would like to speak in English, please say English."
            ],
        )
        self.assertEqual(
            spanish_tts.texts,
            [
                "Gracias por llamar a Blue Sardine Altea. "
                "Si desea continuar en espanol, diga espanol."
            ],
        )

    def test_english_selection_uses_current_tts_and_locked_agent(self):
        fake_settings = self._build_fake_settings(enabled=True)
        english_tts = FakeTTSModel(2)
        spanish_tts = FakeTTSModel(3)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-2"),
            ),
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=english_tts,
                voice_effect=FakeEffect(9),
                ringback_effect=FakeEffect(1),
                spanish_tts_model=spanish_tts,
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()
            chunks = asyncio.run(
                collect_audio(agent._handle_language_selection(session, "ingles"))
            )

        self.assertEqual(session.language, "english")
        self.assertTrue(session.language_selection_complete)
        self.assertIs(session.tts_model, english_tts)
        self.assertEqual(session.react_agent, "english-agent")
        self.assertEqual([int(chunk[1][0]) for chunk in chunks], [2])

    def test_spanish_selection_uses_spanish_tts_and_locked_agent(self):
        fake_settings = self._build_fake_settings(enabled=True)
        english_tts = FakeTTSModel(2)
        spanish_tts = FakeTTSModel(3)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-3"),
            ),
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=english_tts,
                voice_effect=FakeEffect(9),
                ringback_effect=FakeEffect(1),
                spanish_tts_model=spanish_tts,
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()
            chunks = asyncio.run(
                collect_audio(agent._handle_language_selection(session, "espanol"))
            )

        self.assertEqual(session.language, "spanish")
        self.assertTrue(session.language_selection_complete)
        self.assertIs(session.tts_model, spanish_tts)
        self.assertEqual(session.react_agent, "spanish-agent")
        self.assertEqual([int(chunk[1][0]) for chunk in chunks], [3])

    def test_retry_twice_then_defaults_to_spanish(self):
        fake_settings = self._build_fake_settings(enabled=True)
        english_tts = FakeTTSModel(2)
        spanish_tts = FakeTTSModel(3)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-4"),
            ),
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=english_tts,
                voice_effect=FakeEffect(9),
                ringback_effect=FakeEffect(1),
                spanish_tts_model=spanish_tts,
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()
            first_retry = asyncio.run(
                collect_audio(agent._handle_language_selection(session, "hotel"))
            )
            second_retry = asyncio.run(
                collect_audio(agent._handle_language_selection(session, "ninguno"))
            )
            defaulted = asyncio.run(
                collect_audio(agent._handle_language_selection(session, "otra vez"))
            )

        self.assertFalse(session.failed_selection_attempts)
        self.assertEqual(session.language, "spanish")
        self.assertTrue(session.language_selection_complete)
        self.assertEqual([int(chunk[1][0]) for chunk in first_retry], [2, 3])
        self.assertEqual([int(chunk[1][0]) for chunk in second_retry], [2, 3])
        self.assertEqual([int(chunk[1][0]) for chunk in defaulted], [3])

    def test_feature_off_keeps_default_session_routing(self):
        fake_settings = self._build_fake_settings(enabled=False)
        english_tts = FakeTTSModel(2)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-5"),
            ),
            patch.object(
                FastRTCAgent, "_create_react_agent", return_value="default-agent"
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=english_tts,
                voice_effect=FakeEffect(9),
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()

        self.assertTrue(session.language_selection_complete)
        self.assertIsNone(session.language)
        self.assertIs(session.tts_model, english_tts)
        self.assertEqual(session.react_agent, "default-agent")

    def test_missing_spanish_api_url_fails_fast_when_feature_enabled(self):
        fake_settings = self._build_fake_settings(enabled=True)
        fake_settings.orpheus_spanish.api_url = ""

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            with self.assertRaises(ValueError):
                FastRTCAgent(
                    stt_model=object(),
                    tts_model=FakeTTSModel(2),
                    voice_effect=FakeEffect(9),
                    tools=[search_hotel_kb_tool],
                )

    def test_ringback_effect_uses_configured_duration(self):
        fake_settings = self._build_fake_settings(enabled=True)

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_ringback_effect",
                return_value=FakeEffect(1),
            ) as mock_get_ringback,
            patch.object(
                FastRTCAgent,
                "_create_react_agent",
                side_effect=["default-agent", "english-agent", "spanish-agent"],
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            FastRTCAgent(
                stt_model=object(),
                tts_model=FakeTTSModel(2),
                voice_effect=FakeEffect(9),
                spanish_tts_model=FakeTTSModel(3),
                tools=[search_hotel_kb_tool],
            )

        mock_get_ringback.assert_called_once_with(max_duration_s=1.0)


class FastRTCAgentSmokeTests(unittest.TestCase):
    def test_hotel_agent_wires_injected_models_and_tools(self):
        fake_stream = object()
        fake_react_agent = object()
        fake_stt = object()
        fake_tts = object()
        fake_effect = object()

        with (
            patch.object(
                FastRTCAgent, "_create_react_agent", return_value=fake_react_agent
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=fake_stream),
        ):
            agent = FastRTCAgent(
                stt_model=fake_stt,
                tts_model=fake_tts,
                voice_effect=fake_effect,
                tools=[search_hotel_kb_tool],
            )

        self.assertIs(agent.stt_model, fake_stt)
        self.assertIs(agent.tts_model, fake_tts)
        self.assertIs(agent.react_agent, fake_react_agent)
        self.assertIs(agent.stream, fake_stream)
        self.assertIn("Blue Sardine Assistant", DEFAULT_SYSTEM_PROMPT)


class VoiceRouteTests(unittest.TestCase):
    def test_build_telephone_twiml_streams_without_spoken_preamble(self):
        request = FastAPIRequest(
            {
                "type": "http",
                "method": "POST",
                "scheme": "https",
                "path": "/voice/telephone/incoming",
                "headers": [
                    (b"host", b"localhost:8000"),
                    (b"x-forwarded-host", b"demo.example.com"),
                    (b"x-forwarded-proto", b"https"),
                ],
                "query_string": b"",
                "server": ("localhost", 8000),
                "client": ("127.0.0.1", 12345),
                "http_version": "1.1",
            }
        )

        twiml = _build_telephone_twiml(request, "/voice")

        self.assertIn('wss://demo.example.com/voice/telephone/handler', twiml)
        self.assertNotIn("Connecting to the AI assistant.", twiml)
        self.assertNotIn("The call has been disconnected.", twiml)

    def test_replace_telephone_incoming_route_replaces_existing_mount_route(self):
        app = FastAPI()
        app.add_api_route(
            "/voice/telephone/incoming",
            lambda: None,
            methods=["POST"],
            include_in_schema=False,
        )

        _replace_telephone_incoming_route(app, "/voice")

        matching_routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) == "/voice/telephone/incoming"
        ]
        self.assertEqual(len(matching_routes), 1)
        self.assertEqual(matching_routes[0].methods, {"GET", "POST"})


class RunPodLauncherTests(unittest.TestCase):
    def test_orpheus_pod_helper_supports_english_and_spanish_variants(self):
        module = load_orpheus_pod_module()
        english = module.get_orpheus_variant_config("english")
        spanish = module.get_orpheus_variant_config("spanish")

        self.assertEqual(english.env_var_name, "ORPHEUS__API_URL")
        self.assertEqual(spanish.env_var_name, "ORPHEUS_SPANISH__API_URL")
        self.assertEqual(
            spanish.hf_repo,
            "GianDiego/3b-es_it-ft-research_release-Q8-0-GGUF",
        )
        self.assertEqual(spanish.hf_file, "3b-es_it-ft-research_release.q8_0.gguf")
        self.assertEqual(spanish.ctx_size, "2048")

    def test_orpheus_pod_request_uses_variant_specific_env(self):
        module = load_orpheus_pod_module()
        with patch.object(
            module,
            "settings",
            SimpleNamespace(
                runpod=SimpleNamespace(
                    orpheus_image_name="orpheus-image",
                    orpheus_gpu_type="GPU-A",
                )
            ),
        ):
            request = module.build_orpheus_pod_request("spanish")

        self.assertEqual(request["image_name"], "orpheus-image")
        self.assertEqual(request["gpu_type_id"], "GPU-A")
        self.assertEqual(
            request["env"]["LLAMA_ARG_HF_REPO"],
            "GianDiego/3b-es_it-ft-research_release-Q8-0-GGUF",
        )
        self.assertEqual(
            request["env"]["LLAMA_ARG_HF_FILE"],
            "3b-es_it-ft-research_release.q8_0.gguf",
        )
        self.assertEqual(request["env"]["LLAMA_ARG_CTX_SIZE"], "2048")


class LauncherTests(unittest.TestCase):
    def test_launcher_uses_env_defaults_when_not_interactive(self):
        module = load_gradio_launcher_module()
        with patch.object(
            module,
            "settings",
            SimpleNamespace(stt_model="faster-whisper", tts_model="orpheus-runpod"),
        ):
            self.assertEqual(
                module.resolve_model_selection(False),
                ("faster-whisper", "orpheus-runpod"),
            )

    def test_launcher_delegates_to_interactive_selector(self):
        module = load_gradio_launcher_module()
        with (
            patch.object(
                module,
                "settings",
                SimpleNamespace(stt_model="faster-whisper", tts_model="orpheus-runpod"),
            ),
            patch.object(
                module,
                "select_models_interactively",
                return_value=("moonshine", "kokoro"),
            ) as selector,
        ):
            self.assertEqual(
                module.resolve_model_selection(True),
                ("moonshine", "kokoro"),
            )
            selector.assert_called_once_with("faster-whisper", "orpheus-runpod")

    def test_launcher_parser_supports_interactive_flag(self):
        module = load_gradio_launcher_module()
        args = module.build_parser().parse_args(["--interactive-models"])
        self.assertTrue(args.interactive_models)


if __name__ == "__main__":
    unittest.main()
