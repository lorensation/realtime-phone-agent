import inspect
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Literal, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastrtc import ReplyOnPause
from fastrtc.utils import get_current_context
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from realtime_phone_agents.agent.stream import VoiceAgentStream
from realtime_phone_agents.agent.prompts.builder import build_system_prompt
from realtime_phone_agents.agent.prompts.defaults import (
    DEFAULT_LANGUAGE_POLICY,
    LOCAL_PROMPT_FALLBACKS,
    LOCKED_LANGUAGE_POLICY,
)
from realtime_phone_agents.agent.retrieval import build_retrieval_context
from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.agent.utils import model_has_tool_calls
from realtime_phone_agents.config import settings
from realtime_phone_agents.observability.opik_utils import build_langchain_callbacks
from realtime_phone_agents.stt import get_stt_model
from realtime_phone_agents.tts import get_tts_model
from realtime_phone_agents.tts.base import TTSModel
from realtime_phone_agents.voice import get_ringback_effect, get_sound_effect

AudioChunk = Tuple[int, np.ndarray]  # (sample_rate, samples)
SelectedLanguage = Literal["english", "spanish"]

DEFAULT_SYSTEM_PROMPT = "\n\n".join(
    [
        LOCAL_PROMPT_FALLBACKS["core"],
        LOCAL_PROMPT_FALLBACKS["retrieval"],
        LOCAL_PROMPT_FALLBACKS["escalation"],
        LOCAL_PROMPT_FALLBACKS["style"],
        DEFAULT_LANGUAGE_POLICY,
    ]
)
ENGLISH_SYSTEM_PROMPT = "\n\n".join(
    [DEFAULT_SYSTEM_PROMPT, LOCKED_LANGUAGE_POLICY["english"]]
)
SPANISH_SYSTEM_PROMPT = "\n\n".join(
    [
        "\n\n".join(
            [
                LOCAL_PROMPT_FALLBACKS["core"],
                LOCAL_PROMPT_FALLBACKS["retrieval"],
                LOCAL_PROMPT_FALLBACKS["escalation"],
                LOCAL_PROMPT_FALLBACKS["style"],
            ]
        ),
        LOCKED_LANGUAGE_POLICY["spanish"],
    ]
)

ENGLISH_TOOL_USE_MESSAGE = "One moment."
SPANISH_TOOL_USE_MESSAGE = "Un momento."
ENGLISH_FALLBACK_MESSAGE = "I do not have that confirmed right now. You can confirm it directly with the hotel by phone or email."
SPANISH_FALLBACK_MESSAGE = "No tengo ese dato confirmado ahora mismo. Puedes confirmarlo con el alojamiento por telefono o email."

INITIAL_LANGUAGE_PROMPT_EN = (
    "Thank you for calling Blue Sardine Altea. "
    "If you would like to speak in English, please say English."
)
INITIAL_LANGUAGE_PROMPT_ES = (
    "Gracias por llamar a Blue Sardine Altea. "
    "Si desea continuar en espanol, diga espanol."
)
RETRY_LANGUAGE_PROMPT_EN = "Sorry, I did not catch that. Please say English."
RETRY_LANGUAGE_PROMPT_ES = "Lo siento, no lo he entendido. Por favor, diga espanol."
ENGLISH_GREETING = "Thank you. I will assist you in English. How can I help you today?"
SPANISH_GREETING = "Gracias. Le atendere en espanol. En que puedo ayudarle hoy?"
SPANISH_SELECTION_FALLBACK = "No he podido confirmar el idioma. Continuare en espanol. En que puedo ayudarle hoy?"

ENGLISH_SELECTION_KEYWORDS = ("english", "ingles")
SPANISH_SELECTION_KEYWORDS = ("espanol", "spanish", "castellano")
_SENTENCE_SPLIT = re.compile(r"(?<=[\.\!\?])\s+")
_MARKDOWN_BULLET = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")
_INLINE_MARKDOWN = re.compile(r"[*_`#]+")


def normalize_language_selection_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.lower().strip()


def classify_language_selection(text: str) -> Optional[SelectedLanguage]:
    normalized = normalize_language_selection_text(text)
    if not normalized:
        return None

    matches: list[tuple[int, SelectedLanguage]] = []
    for keyword in ENGLISH_SELECTION_KEYWORDS:
        if (position := normalized.find(keyword)) != -1:
            matches.append((position, "english"))
    for keyword in SPANISH_SELECTION_KEYWORDS:
        if (position := normalized.find(keyword)) != -1:
            matches.append((position, "spanish"))

    if not matches:
        return None

    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def chunk_text(text: str, max_chars: int = 240) -> list[str]:
    normalized_text = (text or "").strip()
    if not normalized_text:
        return []
    if len(normalized_text) <= max_chars:
        return [normalized_text]

    chunks: list[str] = []
    current = ""
    for sentence in _SENTENCE_SPLIT.split(normalized_text):
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            oversized_chunk = ""
            for word in sentence.split():
                candidate = (
                    f"{oversized_chunk} {word}".strip() if oversized_chunk else word
                )
                if len(candidate) <= max_chars:
                    oversized_chunk = candidate
                    continue

                if oversized_chunk:
                    chunks.append(oversized_chunk)
                if len(word) <= max_chars:
                    oversized_chunk = word
                    continue

                for start in range(0, len(word), max_chars):
                    chunks.append(word[start : start + max_chars].strip())
                oversized_chunk = ""

            if oversized_chunk:
                chunks.append(oversized_chunk)
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue

        chunks.append(current)
        current = sentence

    if current:
        chunks.append(current)
    return chunks


def normalize_spoken_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = _MARKDOWN_BULLET.sub("", line)
        line = _INLINE_MARKDOWN.sub("", line)
        line = line.replace("•", " ")
        line = line.replace("–", ", ")
        line = line.replace("—", ", ")
        line = line.replace("‑", "-")
        cleaned_lines.append(line.strip())

    normalized = " ".join(cleaned_lines)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


@dataclass
class CallSessionState:
    call_id: str
    thread_id: str = field(default_factory=lambda: str(uuid4()))
    language: Optional[SelectedLanguage] = None
    language_selection_complete: bool = False
    failed_selection_attempts: int = 0
    react_agent: Any | None = None
    tts_model: TTSModel | None = None
    tool_use_message: str = SPANISH_TOOL_USE_MESSAGE
    fallback_message: str = SPANISH_FALLBACK_MESSAGE
    last_final_text: Optional[str] = None
    last_detected_intent: Optional[str] = None
    last_retrieval_metadata: dict[str, Any] = field(default_factory=dict)
    prompt_played: bool = False


class FastRTCAgent:
    """
    Simplified FastRTC agent that encapsulates speech-to-text, agent reasoning,
    and text-to-speech for one or many simultaneous calls.
    """

    def __init__(
        self,
        tool_use_message: str = SPANISH_TOOL_USE_MESSAGE,
        sound_effect_seconds: float = 3.0,
        stt_model=None,
        tts_model=None,
        voice_effect=None,
        ringback_effect=None,
        spanish_tts_model=None,
        thread_id: str = "default",
        fallback_message: str = SPANISH_FALLBACK_MESSAGE,
        system_prompt: str | None = None,
        tools: List | None = None,
        language_locked: SelectedLanguage | None = None,
        can_interrupt: bool = True,
    ):
        self._language_locked = language_locked
        self._custom_system_prompt = system_prompt
        self._custom_tools = tools
        self._last_prompt_refresh_at = time.monotonic()
        self._stt_model = stt_model or get_stt_model(settings.stt_model)
        self._tts_model = tts_model or get_tts_model(
            settings.tts_model,
            language=self._language_code(language_locked),
        )
        self._voice_effect = voice_effect or get_sound_effect()
        self._language_selection_enabled = (
            settings.call_flow.language_selection_enabled
            and self._language_locked is None
        )
        self._selection_retry_limit = settings.call_flow.selection_retry_limit
        self._can_interrupt = can_interrupt
        self._ringback_effect = ringback_effect or get_ringback_effect(
            max_duration_s=settings.call_flow.ringback_seconds
        )
        self._sessions: dict[str, CallSessionState] = {}

        self._react_agent = None
        self._english_react_agent = None
        self._spanish_react_agent = None
        self._english_tts_model = None
        self._spanish_tts_model = None
        self._refresh_react_agents(force=True)
        if self._language_selection_enabled or self._language_locked is not None:
            self._english_tts_model = (
                self._tts_model
                if tts_model is not None
                else self._build_language_tts_model("english")
            )
            if spanish_tts_model is not None:
                self._spanish_tts_model = spanish_tts_model
            elif self._language_selection_enabled or self._language_locked == "spanish":
                self._spanish_tts_model = self._build_language_tts_model("spanish")

        self._thread_id = thread_id
        self._fallback_message = fallback_message
        self._tool_use_message = tool_use_message
        self._sound_effect_seconds = sound_effect_seconds
        self._stream = self._build_stream()

    def _language_code(self, language: SelectedLanguage | None) -> str | None:
        if language == "english":
            return "en-US"
        if language == "spanish":
            return "es-ES"
        return None

    def _stt_language_hint(self, language: SelectedLanguage | None) -> str | None:
        if language == "english":
            return "en"
        if language == "spanish":
            return "es"
        return None

    def _build_language_tts_model(self, language: SelectedLanguage) -> TTSModel:
        return get_tts_model(
            settings.tts_model,
            language=self._language_code(language),
        )

    def _create_react_agent(
        self,
        system_prompt: str | None = None,
        tools: List | None = None,
        language_lock: SelectedLanguage | None = None,
    ):
        llm = ChatGroq(
            model=settings.groq.model,
            api_key=settings.groq.api_key,
        )
        if system_prompt is not None:
            prompt_text = system_prompt
            prompt_telemetry = {"prompt.inline.source": "custom"}
        else:
            built_prompt = build_system_prompt(language_lock=language_lock)
            prompt_text = built_prompt.text
            prompt_telemetry = built_prompt.telemetry

        agent = create_agent(
            llm,
            checkpointer=InMemorySaver(),
            system_prompt=prompt_text,
            tools=tools or [search_hotel_kb_tool],
        )
        setattr(agent, "_prompt_telemetry", prompt_telemetry)
        return agent

    def _refresh_react_agents(self, *, force: bool = False) -> None:
        refresh_interval = max(settings.prompts.refresh_interval_seconds, 0)
        if not force and refresh_interval > 0:
            if (time.monotonic() - self._last_prompt_refresh_at) < refresh_interval:
                return
        if not force:
            build_system_prompt.cache_clear()

        self._react_agent = self._create_react_agent(
            system_prompt=self._custom_system_prompt,
            tools=self._custom_tools,
            language_lock=None,
        )
        if self._language_selection_enabled or self._language_locked is not None:
            self._english_react_agent = self._create_react_agent(
                system_prompt=self._custom_system_prompt,
                tools=self._custom_tools,
                language_lock="english",
            )
            self._spanish_react_agent = self._create_react_agent(
                system_prompt=self._custom_system_prompt,
                tools=self._custom_tools,
                language_lock="spanish",
            )
        self._last_prompt_refresh_at = time.monotonic()

    def _build_stream(self) -> VoiceAgentStream:
        async def handler_wrapper(audio: AudioChunk) -> AsyncIterator[AudioChunk]:
            async for chunk in self._process_audio(audio):
                yield chunk

        startup_fn = self._startup_prompt if self._language_selection_enabled else None
        return VoiceAgentStream(
            handler=ReplyOnPause(
                handler_wrapper,
                startup_fn=startup_fn,
                can_interrupt=self._can_interrupt,
            ),
            modality="audio",
            mode="send-receive",
        )

    def _get_call_id(self) -> str:
        try:
            return get_current_context().webrtc_id
        except RuntimeError:
            return self._thread_id

    def _get_session(self) -> CallSessionState:
        call_id = self._get_call_id()
        session = self._sessions.get(call_id)
        if session is None:
            self._refresh_react_agents()
            session = CallSessionState(call_id=call_id)
            self._sessions[call_id] = session
            if not self._language_selection_enabled:
                self._configure_default_session(session)
        return session

    def _configure_default_session(self, session: CallSessionState) -> None:
        if self._language_locked is not None:
            self._configure_session_language(session, self._language_locked)
            return

        session.language = None
        session.language_selection_complete = True
        session.react_agent = self._react_agent
        session.tts_model = self._tts_model
        session.tool_use_message = self._tool_use_message
        session.fallback_message = self._fallback_message

    def _configure_session_language(
        self, session: CallSessionState, language: SelectedLanguage
    ) -> None:
        session.language = language
        session.language_selection_complete = True
        session.failed_selection_attempts = 0
        if language == "english":
            session.react_agent = self._english_react_agent or self._react_agent
            session.tts_model = self._english_tts_model or self._tts_model
            session.tool_use_message = ENGLISH_TOOL_USE_MESSAGE
            session.fallback_message = ENGLISH_FALLBACK_MESSAGE
            return

        session.react_agent = self._spanish_react_agent or self._react_agent
        session.tts_model = self._spanish_tts_model or self._tts_model
        session.tool_use_message = SPANISH_TOOL_USE_MESSAGE
        session.fallback_message = SPANISH_FALLBACK_MESSAGE

    async def _startup_prompt(self) -> AsyncIterator[AudioChunk]:
        session = self._get_session()
        if session.prompt_played:
            return

        session.prompt_played = True
        async for audio_chunk in self._play_ringback():
            yield audio_chunk
        async for audio_chunk in self._play_language_prompt(retry=False):
            yield audio_chunk

    async def _process_audio(
        self,
        audio: AudioChunk,
    ) -> AsyncIterator[AudioChunk]:
        session = self._get_session()
        transcription = await self._transcribe(audio, language=session.language)
        logger.info(f"Transcription: {transcription}")

        if self._language_selection_enabled and not session.language_selection_complete:
            async for audio_chunk in self._handle_language_selection(
                session, transcription
            ):
                yield audio_chunk
            return

        if not (transcription or "").strip():
            logger.debug("Skipping empty transcription for call {}", session.call_id)
            return

        async for audio_chunk in self._process_with_agent(session, transcription):
            if audio_chunk is not None:
                yield audio_chunk

        final_response = await self._get_final_response(session)
        logger.info(f"Final response: {final_response}")

        if final_response:
            async for audio_chunk in self._synthesize_speech(session, final_response):
                yield audio_chunk

    async def _transcribe(
        self,
        audio: AudioChunk,
        *,
        language: SelectedLanguage | None = None,
    ) -> str:
        stt_kwargs: dict[str, str] = {}
        if language_hint := self._stt_language_hint(language):
            stt_kwargs["language"] = language_hint
        return self._stt_model.stt(audio, **stt_kwargs)

    async def _handle_language_selection(
        self,
        session: CallSessionState,
        transcription: str,
    ) -> AsyncIterator[AudioChunk]:
        selected_language = classify_language_selection(transcription)
        if selected_language:
            self._configure_session_language(session, selected_language)
            greeting = (
                ENGLISH_GREETING if selected_language == "english" else SPANISH_GREETING
            )
            async for audio_chunk in self._synthesize_speech(session, greeting):
                yield audio_chunk
            return

        session.failed_selection_attempts += 1
        if session.failed_selection_attempts <= self._selection_retry_limit:
            async for audio_chunk in self._play_language_prompt(retry=True):
                yield audio_chunk
            return

        logger.info("Language selection unclear. Defaulting to Spanish.")
        self._configure_session_language(session, "spanish")
        async for audio_chunk in self._synthesize_speech(
            session, SPANISH_SELECTION_FALLBACK
        ):
            yield audio_chunk

    async def _play_language_prompt(self, retry: bool) -> AsyncIterator[AudioChunk]:
        english_prompt = (
            RETRY_LANGUAGE_PROMPT_EN if retry else INITIAL_LANGUAGE_PROMPT_EN
        )
        spanish_prompt = (
            RETRY_LANGUAGE_PROMPT_ES if retry else INITIAL_LANGUAGE_PROMPT_ES
        )
        async for audio_chunk in self._synthesize_text_with_model(
            self._tts_model, english_prompt
        ):
            yield audio_chunk
        async for audio_chunk in self._synthesize_text_with_model(
            self._spanish_tts_model or self._tts_model, spanish_prompt
        ):
            yield audio_chunk

    async def _process_with_agent(
        self,
        session: CallSessionState,
        transcription: str,
    ) -> AsyncIterator[Optional[AudioChunk]]:
        final_text: str | None = None
        lookup_preamble_emitted = False
        lookup_sound_emitted = False
        start_time = time.perf_counter()
        session.last_final_text = None
        react_agent = session.react_agent or self._react_agent
        retrieval_context = build_retrieval_context(
            transcription,
            language="en-US" if session.language == "english" else None,
        )
        session.last_detected_intent = retrieval_context.intent
        session.last_retrieval_metadata = retrieval_context.as_metadata()
        metadata = {
            "call_id": session.call_id,
            "thread_id": session.thread_id,
            "language": session.language or "auto",
        }
        metadata.update(session.last_retrieval_metadata)
        metadata.update(self._get_prompt_metadata(react_agent))
        tags = ["voice-agent", f"language:{session.language or 'auto'}"]
        if retrieval_context.intent:
            tags.append(f"intent:{retrieval_context.intent}")
        callbacks = build_langchain_callbacks(
            thread_id=session.thread_id,
            tags=tags,
            metadata=metadata,
        )
        config: dict[str, Any] = {
            "configurable": {"thread_id": session.thread_id},
            "metadata": metadata,
            "tags": tags,
        }
        if callbacks:
            config["callbacks"] = callbacks

        async for chunk in react_agent.astream(
            {"messages": [{"role": "user", "content": transcription}]},
            config,
            stream_mode="updates",
        ):
            for step, data in chunk.items():
                if step == "model" and model_has_tool_calls(data):
                    elapsed_seconds = time.perf_counter() - start_time
                    if (
                        not lookup_preamble_emitted
                        and self._should_emit_lookup_preamble(
                            session, retrieval_context, elapsed_seconds
                        )
                    ):
                        lookup_preamble_emitted = True
                        async for audio_chunk in self._synthesize_speech(
                            session, session.tool_use_message
                        ):
                            yield audio_chunk

                    if (
                        not lookup_sound_emitted
                        and self._sound_effect_seconds > 0
                        and self._should_emit_lookup_sound(
                            retrieval_context, elapsed_seconds
                        )
                    ):
                        lookup_sound_emitted = True
                        async for effect_chunk in self._play_sound_effect():
                            yield effect_chunk

                if step == "model":
                    final_text = self._extract_final_text(data)

        session.last_final_text = final_text

    def _get_prompt_metadata(self, react_agent: Any) -> dict[str, Any]:
        prompt_metadata = getattr(react_agent, "_prompt_telemetry", {})
        return dict(prompt_metadata) if isinstance(prompt_metadata, dict) else {}

    def _should_emit_lookup_preamble(
        self,
        session: CallSessionState,
        retrieval_context,
        elapsed_seconds: float,
    ) -> bool:
        mode = settings.call_flow.tool_use_preamble_mode
        if mode == "always":
            return True
        if mode == "never":
            return False
        if elapsed_seconds >= settings.call_flow.lookup_latency_threshold_ms / 1000:
            return True
        if retrieval_context.search_mode != "factual":
            return True
        if retrieval_context.intent in {"availability_pricing", "special_requests"}:
            return True
        if retrieval_context.filters.policy_type in {"payment", "cancellation"}:
            return True
        return len(retrieval_context.query.split()) > 14

    def _should_emit_lookup_sound(
        self,
        retrieval_context,
        elapsed_seconds: float,
    ) -> bool:
        mode = settings.call_flow.lookup_sound_mode
        if mode == "always":
            return True
        if mode == "never":
            return False
        if elapsed_seconds >= settings.call_flow.lookup_latency_threshold_ms / 1000:
            return True
        if retrieval_context.search_mode in {"handoff", "style"}:
            return True
        return len(retrieval_context.query.split()) > 18

    def _extract_final_text(self, model_step_data) -> Optional[str]:
        msgs = model_step_data.get("messages", [])
        if isinstance(msgs, list) and len(msgs) > 0:
            return getattr(msgs[0], "content", None)
        return None

    async def _get_final_response(self, session: CallSessionState) -> str:
        return normalize_spoken_text(session.last_final_text or session.fallback_message)

    async def _synthesize_text_with_model(
        self,
        model: TTSModel,
        text: str,
    ) -> AsyncIterator[AudioChunk]:
        segments = chunk_text(text, max_chars=120)
        if not segments:
            return

        supports_context = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            or parameter.name in {"previous_text", "next_text"}
            for parameter in inspect.signature(model.stream_tts).parameters.values()
        )

        for index, segment in enumerate(segments):
            kwargs: dict[str, str] = {}
            if supports_context:
                if index > 0:
                    kwargs["previous_text"] = segments[index - 1]
                if index + 1 < len(segments):
                    kwargs["next_text"] = segments[index + 1]

            async for audio_chunk in model.stream_tts(segment, **kwargs):
                yield audio_chunk

    async def _synthesize_speech(
        self,
        session: CallSessionState,
        text: str,
    ) -> AsyncIterator[AudioChunk]:
        tts_model = session.tts_model or self._tts_model
        async for audio_chunk in self._synthesize_text_with_model(
            tts_model, normalize_spoken_text(text)
        ):
            yield audio_chunk

    async def _play_sound_effect(self) -> AsyncIterator[AudioChunk]:
        async for effect_chunk in self._voice_effect.stream():
            yield effect_chunk

    async def _play_ringback(self) -> AsyncIterator[AudioChunk]:
        async for effect_chunk in self._ringback_effect.stream():
            yield effect_chunk

    @property
    def stream(self) -> VoiceAgentStream:
        return self._stream

    @property
    def stt_model(self):
        return self._stt_model

    @property
    def tts_model(self):
        return self._tts_model

    @property
    def react_agent(self):
        return self._react_agent

    @property
    def voice_effect(self):
        return self._voice_effect

    def set_thread_id(self, thread_id: str) -> None:
        self._thread_id = thread_id

    def set_fallback_message(self, message: str) -> None:
        self._fallback_message = message

    def set_tool_use_message(self, message: str) -> None:
        self._tool_use_message = message

    def set_sound_effect_seconds(self, seconds: float) -> None:
        self._sound_effect_seconds = seconds
