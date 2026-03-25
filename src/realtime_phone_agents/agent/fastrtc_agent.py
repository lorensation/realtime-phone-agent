import unicodedata
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Literal, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastrtc import ReplyOnPause, Stream
from fastrtc.utils import get_current_context
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.agent.utils import model_has_tool_calls
from realtime_phone_agents.config import settings
from realtime_phone_agents.stt import get_stt_model
from realtime_phone_agents.tts import get_tts_model
from realtime_phone_agents.tts.base import TTSModel
from realtime_phone_agents.tts.runpod import OrpheusTTSModel, OrpheusTTSOptions
from realtime_phone_agents.voice import get_ringback_effect, get_sound_effect

AudioChunk = Tuple[int, np.ndarray]  # (sample_rate, samples)
SelectedLanguage = Literal["english", "spanish"]

COMMON_SYSTEM_PROMPT = """
Your name is Blue Sardine Assistant, and you help guests of Blue Sardine Altea.
Your role is to answer guest questions about rooms, services, policies, parking, location, and orientative pricing.
You must use the search_hotel_kb_tool whenever you need factual hotel information.

Trust and policy rules:
Use only facts from the tool or from the user's input.
Prefer official information over everything else.
Treat internal_unvalidated pricing as orientative only.
Treat third_party room type details as unconfirmed and say they require direct confirmation.
If the tool says something is not confirmed, say so clearly and offer the phone or email contact.
If the guest asks for pricing without exact stay dates, ask for exact dates first.
If no booking engine is available, describe prices as orientative starting prices only.
If a policy blocks a request, explain it briefly and offer a nearby alternative when possible.

Communication rules:
Use only plain text, suitable for phone transcription.
Do not use emojis, asterisks, bullet points, or any special formatting.
Keep answers concise, friendly, and easy to follow.
Include exact operational details when needed, such as check-in times, prices, address, phone, or email.
Do not invent amenities, prices, availability, or room details.

When presenting multiple room options, separate them with simple sentences, maintaining clarity and brevity.
""".strip()

DEFAULT_SYSTEM_PROMPT = (
    f"{COMMON_SYSTEM_PROMPT}\n"
    "Reply in Spanish by default. If the guest speaks in English or explicitly asks for English, reply in English."
)

ENGLISH_SYSTEM_PROMPT = (
    f"{COMMON_SYSTEM_PROMPT}\n"
    "The caller explicitly selected English at the start of the call. Reply only in English for the entire call."
)

SPANISH_SYSTEM_PROMPT = (
    f"{COMMON_SYSTEM_PROMPT}\n"
    "La persona que llama eligio espanol al inicio de la llamada. Responda solo en espanol durante toda la llamada."
)

ENGLISH_TOOL_USE_MESSAGE = "I am checking the hotel information."
SPANISH_TOOL_USE_MESSAGE = "Estoy revisando la informacion del hotel."
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
RETRY_LANGUAGE_PROMPT_ES = (
    "Lo siento, no lo he entendido. Por favor, diga espanol."
)
ENGLISH_GREETING = "Thank you. I will assist you in English. How can I help you today?"
SPANISH_GREETING = "Gracias. Le atendere en espanol. En que puedo ayudarle hoy?"
SPANISH_SELECTION_FALLBACK = "No he podido confirmar el idioma. Continuare en espanol. En que puedo ayudarle hoy?"

ENGLISH_SELECTION_KEYWORDS = ("english", "ingles")
SPANISH_SELECTION_KEYWORDS = ("espanol", "spanish", "castellano")


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
    ):
        self._stt_model = stt_model or get_stt_model(settings.stt_model)
        self._tts_model = tts_model or get_tts_model(settings.tts_model)
        self._voice_effect = voice_effect or get_sound_effect()
        self._language_selection_enabled = settings.call_flow.language_selection_enabled
        self._selection_retry_limit = settings.call_flow.selection_retry_limit
        self._ringback_effect = ringback_effect or get_ringback_effect(
            max_duration_s=settings.call_flow.ringback_seconds
        )
        self._sessions: dict[str, CallSessionState] = {}

        self._react_agent = self._create_react_agent(
            system_prompt=system_prompt,
            tools=tools,
        )
        self._english_react_agent = None
        self._spanish_react_agent = None
        self._spanish_tts_model = None
        if self._language_selection_enabled:
            self._english_react_agent = self._create_react_agent(
                system_prompt=self._build_locked_system_prompt(
                    "english", system_prompt
                ),
                tools=tools,
            )
            self._spanish_react_agent = self._create_react_agent(
                system_prompt=self._build_locked_system_prompt(
                    "spanish", system_prompt
                ),
                tools=tools,
            )
            self._spanish_tts_model = (
                spanish_tts_model or self._build_spanish_tts_model()
            )

        self._thread_id = thread_id
        self._fallback_message = fallback_message
        self._tool_use_message = tool_use_message
        self._sound_effect_seconds = sound_effect_seconds
        self._stream = self._build_stream()

    def _build_locked_system_prompt(
        self, language: SelectedLanguage, custom_system_prompt: str | None
    ) -> str:
        if custom_system_prompt:
            if language == "english":
                return (
                    f"{custom_system_prompt}\n"
                    "Language lock: the caller explicitly selected English. Reply only in English for the entire call."
                )
            return (
                f"{custom_system_prompt}\n"
                "Bloqueo de idioma: la persona que llama eligio espanol. Responda solo en espanol durante toda la llamada."
            )
        return ENGLISH_SYSTEM_PROMPT if language == "english" else SPANISH_SYSTEM_PROMPT

    def _build_spanish_tts_model(self) -> OrpheusTTSModel:
        options = OrpheusTTSOptions(
            api_url=settings.orpheus_spanish.api_url,
            model=settings.orpheus_spanish.model,
            voice=settings.orpheus_spanish.voice,
            temperature=settings.orpheus_spanish.temperature,
            top_p=settings.orpheus_spanish.top_p,
            max_tokens=settings.orpheus_spanish.max_tokens,
            repetition_penalty=settings.orpheus_spanish.repetition_penalty,
            sample_rate=settings.orpheus_spanish.sample_rate,
            debug=settings.orpheus_spanish.debug,
        )
        return OrpheusTTSModel(options)

    def _create_react_agent(
        self,
        system_prompt: str | None = None,
        tools: List | None = None,
    ):
        llm = ChatGroq(
            model=settings.groq.model,
            api_key=settings.groq.api_key,
        )

        agent = create_agent(
            llm,
            checkpointer=InMemorySaver(),
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
            tools=tools or [search_hotel_kb_tool],
        )
        return agent

    def _build_stream(self) -> Stream:
        async def handler_wrapper(audio: AudioChunk) -> AsyncIterator[AudioChunk]:
            async for chunk in self._process_audio(audio):
                yield chunk

        startup_fn = self._startup_prompt if self._language_selection_enabled else None
        return Stream(
            handler=ReplyOnPause(handler_wrapper, startup_fn=startup_fn),
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
            session = CallSessionState(call_id=call_id)
            self._sessions[call_id] = session
            if not self._language_selection_enabled:
                self._configure_default_session(session)
        return session

    def _configure_default_session(self, session: CallSessionState) -> None:
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
            session.tts_model = self._tts_model
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
        transcription = await self._transcribe(audio)
        logger.info(f"Transcription: {transcription}")

        if self._language_selection_enabled and not session.language_selection_complete:
            async for audio_chunk in self._handle_language_selection(
                session, transcription
            ):
                yield audio_chunk
            return

        async for audio_chunk in self._process_with_agent(session, transcription):
            if audio_chunk is not None:
                yield audio_chunk

        final_response = await self._get_final_response(session)
        logger.info(f"Final response: {final_response}")

        if final_response:
            async for audio_chunk in self._synthesize_speech(session, final_response):
                yield audio_chunk

    async def _transcribe(self, audio: AudioChunk) -> str:
        return self._stt_model.stt(audio)

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
        session.last_final_text = None
        react_agent = session.react_agent or self._react_agent

        async for chunk in react_agent.astream(
            {"messages": [{"role": "user", "content": transcription}]},
            {"configurable": {"thread_id": session.thread_id}},
            stream_mode="updates",
        ):
            for step, data in chunk.items():
                if step == "model" and model_has_tool_calls(data):
                    async for audio_chunk in self._synthesize_speech(
                        session, session.tool_use_message
                    ):
                        yield audio_chunk

                    if self._sound_effect_seconds > 0:
                        async for effect_chunk in self._play_sound_effect():
                            yield effect_chunk

                if step == "model":
                    final_text = self._extract_final_text(data)

        session.last_final_text = final_text

    def _extract_final_text(self, model_step_data) -> Optional[str]:
        msgs = model_step_data.get("messages", [])
        if isinstance(msgs, list) and len(msgs) > 0:
            return getattr(msgs[0], "content", None)
        return None

    async def _get_final_response(self, session: CallSessionState) -> str:
        return session.last_final_text or session.fallback_message

    async def _synthesize_text_with_model(
        self,
        model: TTSModel,
        text: str,
    ) -> AsyncIterator[AudioChunk]:
        async for audio_chunk in model.stream_tts(text):
            yield audio_chunk

    async def _synthesize_speech(
        self,
        session: CallSessionState,
        text: str,
    ) -> AsyncIterator[AudioChunk]:
        tts_model = session.tts_model or self._tts_model
        async for audio_chunk in self._synthesize_text_with_model(tts_model, text):
            yield audio_chunk

    async def _play_sound_effect(self) -> AsyncIterator[AudioChunk]:
        async for effect_chunk in self._voice_effect.stream():
            yield effect_chunk

    async def _play_ringback(self) -> AsyncIterator[AudioChunk]:
        async for effect_chunk in self._ringback_effect.stream():
            yield effect_chunk

    @property
    def stream(self) -> Stream:
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
