import importlib.util
import base64
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from realtime_phone_agents.agent.fastrtc_agent import (
    DEFAULT_SYSTEM_PROMPT,
    FastRTCAgent,
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
            },
        )

        self.assertEqual(settings.stt_model, "moonshine")
        self.assertEqual(settings.tts_model, "kokoro")
        self.assertEqual(
            settings.faster_whisper.api_url, "https://faster-whisper.example"
        )
        self.assertEqual(settings.orpheus.api_url, "https://orpheus.example")
        self.assertEqual(settings.together.api_key, "together-key")
        self.assertEqual(settings.runpod.orpheus_gpu_type, "GPU-A")


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
