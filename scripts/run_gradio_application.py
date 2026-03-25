# ruff: noqa: E402

import argparse
import logging
import os
import sys
import warnings

# Suppress noisy library logs before importing the app
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logging.getLogger("pydantic_settings").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("superlinked").setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)

try:
    import structlog

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR),
    )
except (ImportError, AttributeError):
    pass

from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent
from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.config import settings
from realtime_phone_agents.infrastructure.superlinked.service import (
    get_knowledge_search_service,
)
from realtime_phone_agents.stt import get_stt_model
from realtime_phone_agents.tts import get_tts_model

STT_CHOICES = [
    ("Moonshine - Local lightweight STT via FastRTC", "moonshine"),
    ("Whisper Groq - Fast cloud Whisper via Groq API", "whisper-groq"),
    ("Faster Whisper - OpenAI-compatible RunPod deployment", "faster-whisper"),
]

TTS_CHOICES = [
    ("Kokoro - Local TTS via FastRTC", "kokoro"),
    ("Together AI - Hosted Orpheus and other TTS models", "together"),
    ("Orpheus RunPod - Self-hosted Orpheus via llama.cpp", "orpheus-runpod"),
]


def print_header() -> None:
    print("\n" + "=" * 60)
    print("Blue Sardine Hotel Voice Agent")
    print("=" * 60)
    print()


def print_success(message: str) -> None:
    print(f"[ok] {message}")


def print_error(message: str) -> None:
    print(f"[error] {message}", file=sys.stderr)


def print_info(message: str) -> None:
    print(f"[info] {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch the Blue Sardine hotel voice agent UI."
    )
    parser.add_argument(
        "--interactive-models",
        action="store_true",
        help="Choose STT and TTS providers interactively instead of using .env values.",
    )
    return parser


def select_models_interactively(
    default_stt: str,
    default_tts: str,
) -> tuple[str, str]:
    try:
        import inquirer
    except ImportError as exc:
        raise RuntimeError(
            "Interactive model selection requires the 'inquirer' package."
        ) from exc

    questions = [
        inquirer.List(
            "stt_model",
            message="Select STT (Speech-to-Text) model",
            choices=STT_CHOICES,
            default=default_stt,
        ),
        inquirer.List(
            "tts_model",
            message="Select TTS (Text-to-Speech) model",
            choices=TTS_CHOICES,
            default=default_tts,
        ),
    ]

    answers = inquirer.prompt(questions)
    if not answers:
        raise RuntimeError("Interactive model selection was cancelled.")

    return answers["stt_model"], answers["tts_model"]


def resolve_model_selection(interactive_models: bool) -> tuple[str, str]:
    if interactive_models:
        return select_models_interactively(settings.stt_model, settings.tts_model)
    return settings.stt_model, settings.tts_model


def main(argv: list[str] | None = None) -> int:
    print_header()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        stt_model_name, tts_model_name = resolve_model_selection(
            args.interactive_models
        )
    except KeyboardInterrupt:
        print("\nModel selection cancelled by user")
        return 0
    except Exception as exc:
        print_error(str(exc))
        return 1

    print_info(f"STT model: {stt_model_name}")
    print_info(f"TTS model: {tts_model_name}")
    print()

    print_info("Loading Blue Sardine knowledge base")
    try:
        get_knowledge_search_service()
        print_success("Knowledge base loaded")
    except Exception as exc:
        print_error(f"Error loading knowledge base: {exc}")
        return 1

    print()
    print_info(f"Initializing {stt_model_name} STT model")
    try:
        stt_model = get_stt_model(stt_model_name)
        print_success("STT model initialized")
    except Exception as exc:
        print_error(f"Error initializing STT model: {exc}")
        return 1

    print_info(f"Initializing {tts_model_name} TTS model")
    try:
        tts_model = get_tts_model(tts_model_name)
        print_success("TTS model initialized")
    except Exception as exc:
        print_error(f"Error initializing TTS model: {exc}")
        return 1

    print()
    print_info("Creating hotel voice agent")
    try:
        agent = FastRTCAgent(
            stt_model=stt_model,
            tts_model=tts_model,
            tools=[search_hotel_kb_tool],
        )
        print_success("FastRTC agent created")
    except Exception as exc:
        print_error(f"Error creating agent: {exc}")
        return 1

    print()
    print_info("Launching Gradio interface")
    print()

    try:
        agent.stream.ui.launch()
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return 0
    except Exception as exc:
        print_error(f"Error launching application: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
