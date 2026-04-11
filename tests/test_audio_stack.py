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
    chunk_text,
    classify_language_selection,
)
from realtime_phone_agents.api.routes.voice import (
    _build_connect_twiml,
    _build_language_gather_twiml,
    _replace_telephone_incoming_route,
    _replace_telephone_language_route,
)
from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.config import Settings
from realtime_phone_agents.stt.runpod.faster_whisper.model import FasterWhisperSTT
from realtime_phone_agents.stt.runpod.faster_whisper.options import (
    FasterWhisperSTTOptions,
)
from realtime_phone_agents.tts.elevenlabs.model import ElevenLabsTTSModel
from realtime_phone_agents.stt.utils import get_stt_model
from realtime_phone_agents.tts.runpod.orpheus.model import OrpheusTTSModel
from realtime_phone_agents.tts.runpod.orpheus.options import OrpheusTTSOptions
from realtime_phone_agents.tts.togetherai.model import TogetherTTSModel
from realtime_phone_agents.tts.togetherai.options import TogetherTTSOptions
from realtime_phone_agents.tts.utils import get_tts_model
from fastapi import FastAPI
from fastapi import Request as FastAPIRequest
from fastapi.testclient import TestClient


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


class OpikDecoratorTests(unittest.TestCase):
    def test_track_returns_noop_decorator_when_opik_is_unavailable(self):
        import realtime_phone_agents.observability.opik_utils as opik_utils

        with patch.object(opik_utils, "opik", None):
            @opik_utils.track(name="noop")
            def decorated():
                return "ok"

        self.assertEqual(decorated(), "ok")


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
            elevenlabs={
                "api_key": "eleven-key",
                "voice_id_es": "voice-es",
                "output_format": "pcm_16000",
            },
            opik={
                "api_key": "opik-key",
                "project_name": "blue-sardine-hotel",
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
        self.assertEqual(settings.elevenlabs.api_key, "eleven-key")
        self.assertEqual(settings.elevenlabs.output_format, "pcm_16000")
        self.assertEqual(settings.opik.project_name, "blue-sardine-hotel")
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

        with patch(
            "realtime_phone_agents.tts.utils.ElevenLabsTTSModel",
            return_value="elevenlabs",
        ):
            self.assertEqual(get_tts_model("elevenlabs-es"), "elevenlabs")

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


class ElevenLabsTTSModelTests(unittest.TestCase):
    def test_elevenlabs_streams_pcm_audio_from_httpx_async_client(self):
        import realtime_phone_agents.tts.elevenlabs.model as eleven_model

        class FakeResponse:
            def __init__(self):
                self.status_code = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            async def aiter_bytes(self):
                for chunk in (b"\x01\x00\x02\x00", b"\x03\x00\x04\x00"):
                    yield chunk

        class FakeClient:
            last_request = None

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def stream(self, method, url, headers=None, params=None, json=None):
                FakeClient.last_request = (method, url, headers, params, json)
                return FakeResponse()

        with patch.object(eleven_model.httpx, "AsyncClient", FakeClient):
            model = ElevenLabsTTSModel(
                api_key="eleven-key",
                model_id="eleven_flash_v2_5",
                voice_id="voice-es",
                output_format="pcm_16000",
            )
            chunks = asyncio.run(
                collect_audio(
                    model.stream_tts(
                        "hola",
                        previous_text="bienvenido",
                        next_text="gracias",
                    )
                )
            )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][0], 16000)
        np.testing.assert_array_equal(
            chunks[0][1], np.frombuffer(b"\x01\x00\x02\x00", dtype=np.int16)
        )
        self.assertEqual(
            FakeClient.last_request[1],
            "https://api.elevenlabs.io/v1/text-to-speech/voice-es/stream",
        )
        self.assertEqual(FakeClient.last_request[3], {"output_format": "pcm_16000"})
        self.assertEqual(FakeClient.last_request[4]["model_id"], "eleven_flash_v2_5")
        self.assertEqual(FakeClient.last_request[4]["language_code"], "es")
        self.assertEqual(
            FakeClient.last_request[4]["apply_text_normalization"], "auto"
        )
        self.assertEqual(FakeClient.last_request[4]["previous_text"], "bienvenido")
        self.assertEqual(FakeClient.last_request[4]["next_text"], "gracias")


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


class RecordingContextTTSModel:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def stream_tts(self, text: str, **kwargs):
        self.calls.append((text, kwargs))
        yield 16000, np.array([len(self.calls)], dtype=np.int16)

    def tts(self, text: str, **kwargs):
        self.calls.append((text, kwargs))
        return 16000, np.array([len(self.calls)], dtype=np.int16)


class FakeMessage:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeStreamingAgent:
    def __init__(self, final_text: str = "respuesta final"):
        self.final_text = final_text
        self._prompt_telemetry = {"prompt.core.source": "test"}

    async def astream(self, *_args, **_kwargs):
        yield {"model": {"messages": [FakeMessage("", tool_calls=[{"id": "tool-1"}])]}}
        yield {"model": {"messages": [FakeMessage(self.final_text)]}}


class ChunkingTests(unittest.TestCase):
    def test_chunk_text_respects_max_chars_and_keeps_order(self):
        text = (
            "Primera frase corta. "
            "Segunda frase tambien corta. "
            "Tercera frase algo mas larga para obligar a crear varios trozos."
        )

        chunks = chunk_text(text, max_chars=40)

        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 40 for chunk in chunks))
        self.assertEqual(" ".join(chunks), text)

    def test_synthesize_text_with_model_streams_segments_in_order(self):
        fake_settings = SimpleNamespace(
            call_flow=SimpleNamespace(
                language_selection_enabled=False,
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
        model = RecordingContextTTSModel()

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                FastRTCAgent, "_create_react_agent", return_value="default-agent"
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=model,
                voice_effect=FakeEffect(9),
                ringback_effect=FakeEffect(1),
                tools=[search_hotel_kb_tool],
            )
            text = (
                "Primera frase corta con informacion sobre horarios y desayuno. "
                "Segunda frase corta con informacion sobre aparcamiento y recepcion. "
                "Tercera frase corta con informacion sobre habitaciones y politicas. "
                "Cuarta frase corta con informacion sobre ubicacion y contacto."
            )
            chunks = asyncio.run(
                collect_audio(
                    agent._synthesize_text_with_model(
                        model,
                        text,
                    )
                )
            )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(" ".join(call[0] for call in model.calls), text)
        self.assertEqual(model.calls[0][1]["next_text"], model.calls[1][0])
        self.assertEqual(
            model.calls[1][1]["previous_text"], model.calls[0][0]
        )


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
                spanish_tts_model=fake_tts,
                voice_effect=fake_effect,
                tools=[search_hotel_kb_tool],
            )

        self.assertIs(agent.stt_model, fake_stt)
        self.assertIs(agent.tts_model, fake_tts)
        self.assertIs(agent.react_agent, fake_react_agent)
        self.assertIs(agent.stream, fake_stream)
        self.assertIn("phone receptionist for Blue Sardine Altea", DEFAULT_SYSTEM_PROMPT)


class LookupCuePolicyTests(unittest.TestCase):
    def _build_fake_settings(self, preamble_mode="auto", sound_mode="auto"):
        return SimpleNamespace(
            call_flow=SimpleNamespace(
                language_selection_enabled=False,
                selection_retry_limit=2,
                ringback_seconds=1.0,
                tool_use_preamble_mode=preamble_mode,
                lookup_sound_mode=sound_mode,
                lookup_latency_threshold_ms=1200,
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

    def test_simple_lookup_does_not_force_preamble_or_sound_in_auto_mode(self):
        fake_settings = self._build_fake_settings()

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-auto-1"),
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=FakeTTSModel(2),
                voice_effect=FakeEffect(9),
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()
            session.react_agent = FakeStreamingAgent("parking confirmado")
            chunks = asyncio.run(
                collect_audio(agent._process_with_agent(session, "Hay parking?"))
            )

        self.assertEqual(chunks, [])
        self.assertEqual(session.last_final_text, "parking confirmado")

    def test_complex_lookup_can_emit_preamble_in_auto_mode(self):
        fake_settings = self._build_fake_settings(sound_mode="never")

        with (
            patch.object(agent_module, "settings", fake_settings),
            patch.object(
                agent_module,
                "get_current_context",
                return_value=SimpleNamespace(webrtc_id="call-auto-2"),
            ),
            patch.object(FastRTCAgent, "_build_stream", return_value=object()),
        ):
            tts_model = FakeTTSModel(2)
            agent = FastRTCAgent(
                stt_model=object(),
                tts_model=tts_model,
                voice_effect=FakeEffect(9),
                tools=[search_hotel_kb_tool],
            )
            session = agent._get_session()
            session.react_agent = FakeStreamingAgent("precio orientativo")
            chunks = asyncio.run(
                collect_audio(
                    agent._process_with_agent(
                        session,
                        (
                            "How much is the studio with terrace if I stay next month "
                            "for two adults and need flexible cancellation?"
                        ),
                    )
                )
            )

        self.assertEqual([int(chunk[1][0]) for chunk in chunks], [2])
        self.assertEqual(tts_model.texts, ["Un momento."])
        self.assertEqual(session.last_final_text, "precio orientativo")


class VoiceRouteTests(unittest.TestCase):
    def test_build_language_gather_twiml_contains_gather_and_action(self):
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

        twiml = _build_language_gather_twiml(request)

        self.assertIn("<Gather", twiml)
        self.assertIn(
            'action="https://demo.example.com/voice/telephone/language?retry=0"',
            twiml,
        )
        self.assertIn('input="dtmf speech"', twiml)
        self.assertIn('actionOnEmptyResult="true"', twiml)
        self.assertIn("For English press two or say English.", twiml)

    def test_build_connect_twiml_routes_to_language_specific_handler(self):
        request = FastAPIRequest(
            {
                "type": "http",
                "method": "POST",
                "scheme": "https",
                "path": "/voice/telephone/language",
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

        twiml = _build_connect_twiml(
            request,
            voice_path="/voice-es",
            greeting="Gracias",
            language="es-ES",
        )

        self.assertIn('wss://demo.example.com/voice-es/telephone/handler', twiml)
        self.assertIn("<Say", twiml)

    def test_replace_telephone_incoming_route_replaces_existing_mount_route(self):
        app = FastAPI()
        app.add_api_route(
            "/voice/telephone/incoming",
            lambda: None,
            methods=["POST"],
            include_in_schema=False,
        )

        _replace_telephone_incoming_route(app)

        matching_routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) == "/voice/telephone/incoming"
        ]
        self.assertEqual(len(matching_routes), 1)
        self.assertEqual(matching_routes[0].methods, {"GET", "POST"})

    def test_language_route_connects_to_spanish_and_english_handlers(self):
        app = FastAPI()
        _replace_telephone_language_route(app)
        client = TestClient(app, base_url="https://demo.example.com")

        spanish = client.post(
            "/voice/telephone/language?retry=0",
            data={"Digits": "1"},
            headers={"x-forwarded-host": "demo.example.com", "x-forwarded-proto": "https"},
        )
        english = client.post(
            "/voice/telephone/language?retry=0",
            data={"Digits": "2"},
            headers={"x-forwarded-host": "demo.example.com", "x-forwarded-proto": "https"},
        )

        self.assertEqual(spanish.status_code, 200)
        self.assertIn(
            'wss://demo.example.com/voice-es/telephone/handler',
            spanish.text,
        )
        self.assertIn(
            'wss://demo.example.com/voice-en/telephone/handler',
            english.text,
        )

    def test_language_route_defaults_to_spanish_after_retry_limit(self):
        app = FastAPI()
        _replace_telephone_language_route(app)
        client = TestClient(app, base_url="https://demo.example.com")

        response = client.post(
            "/voice/telephone/language?retry=2",
            data={"SpeechResult": "no entiendo"},
            headers={"x-forwarded-host": "demo.example.com", "x-forwarded-proto": "https"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'wss://demo.example.com/voice-es/telephone/handler',
            response.text,
        )
        self.assertIn("Continuare en espanol", response.text)


class RunPodLauncherTests(unittest.TestCase):
    def test_orpheus_pod_helper_uses_english_only_configuration(self):
        module = load_orpheus_pod_module()
        config = module.get_orpheus_deployment_config()

        self.assertEqual(config.env_var_name, "ORPHEUS__API_URL")
        self.assertEqual(config.hf_repo, "PkmX/orpheus-3b-0.1-ft-Q8_0-GGUF")
        self.assertEqual(config.hf_file, "orpheus-3b-0.1-ft-q8_0.gguf")
        self.assertEqual(config.voice, "tara")
        self.assertEqual(config.ctx_size, "0")

    def test_orpheus_pod_request_uses_english_model_env(self):
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
            request = module.build_orpheus_pod_request()

        self.assertEqual(request["image_name"], "orpheus-image")
        self.assertEqual(request["gpu_type_id"], "GPU-A")
        self.assertEqual(
            request["env"]["LLAMA_ARG_HF_REPO"],
            "PkmX/orpheus-3b-0.1-ft-Q8_0-GGUF",
        )
        self.assertEqual(
            request["env"]["LLAMA_ARG_HF_FILE"],
            "orpheus-3b-0.1-ft-q8_0.gguf",
        )
        self.assertEqual(request["env"]["LLAMA_ARG_CTX_SIZE"], "0")


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
