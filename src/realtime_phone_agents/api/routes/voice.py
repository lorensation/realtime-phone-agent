from __future__ import annotations

from urllib.parse import urlencode
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from loguru import logger
from twilio.twiml.voice_response import Connect, VoiceResponse

from realtime_phone_agents.agent.fastrtc_agent import (
    ENGLISH_GREETING,
    SPANISH_GREETING,
    SPANISH_SELECTION_FALLBACK,
    FastRTCAgent,
    classify_language_selection,
)
from realtime_phone_agents.config import settings
from realtime_phone_agents.tts import get_tts_model

LANGUAGE_ROUTE_PATH = "/voice/telephone/language"
INCOMING_ROUTE_PATH = "/voice/telephone/incoming"
GATHER_TIMEOUT_SECONDS = 6


def _header_value(request: Request, header_name: str, fallback: str) -> str:
    value = request.headers.get(header_name, fallback)
    return value.split(",")[0].strip()


def _public_host(request: Request) -> str:
    return _header_value(
        request, "x-forwarded-host", request.headers.get("host", "localhost")
    )


def _public_scheme(request: Request) -> str:
    return _header_value(request, "x-forwarded-proto", request.url.scheme)


def _absolute_url(
    request: Request, path: str, query_params: dict[str, str | int] | None = None
) -> str:
    query_string = ""
    if query_params:
        query_string = f"?{urlencode(query_params)}"
    return f"{_public_scheme(request)}://{_public_host(request)}{path}{query_string}"


def _websocket_url(request: Request, path: str) -> str:
    websocket_scheme = "wss" if _public_scheme(request) == "https" else "ws"
    return f"{websocket_scheme}://{_public_host(request)}{path}/telephone/handler"


def _coerce_retry_count(raw_retry: str | None) -> int:
    try:
        return max(int(raw_retry or "0"), 0)
    except ValueError:
        return 0


def _select_language(digits: str, speech_result: str) -> str | None:
    normalized_digits = (digits or "").strip()
    if normalized_digits == "1":
        return "spanish"
    if normalized_digits == "2":
        return "english"

    return classify_language_selection(speech_result or "")


def _build_language_gather_twiml(request: Request, retry_count: int = 0) -> str:
    response = VoiceResponse()
    gather = response.gather(
        input="dtmf speech",
        num_digits=1,
        timeout=GATHER_TIMEOUT_SECONDS,
        speech_timeout="auto",
        language="es-ES",
        action=_absolute_url(
            request,
            LANGUAGE_ROUTE_PATH,
            query_params={"retry": retry_count},
        ),
        method="POST",
        action_on_empty_result=True,
    )

    if retry_count > 0:
        gather.say(
            "No he entendido la seleccion. Para espanol pulse uno o diga espanol.",
            language="es-ES",
        )
        gather.say(
            "I did not catch the selection. For English press two or say English.",
            language="en-US",
        )
    else:
        gather.say(
            "Bienvenido a Blue Sardine Altea. Para espanol pulse uno o diga espanol.",
            language="es-ES",
        )
        gather.say(
            "Welcome to Blue Sardine Altea. For English press two or say English.",
            language="en-US",
        )

    return str(response)


def _build_connect_twiml(
    request: Request,
    *,
    voice_path: str,
    greeting: str | None = None,
    language: str | None = None,
) -> str:
    response = VoiceResponse()
    if greeting:
        response.say(greeting, language=language)

    connect = Connect()
    connect.stream(url=_websocket_url(request, voice_path))
    response.append(connect)
    return str(response)


def _remove_route_if_present(app: FastAPI, route_path: str) -> None:
    app.router.routes[:] = [
        route for route in app.router.routes if getattr(route, "path", None) != route_path
    ]


def _replace_telephone_incoming_route(app: FastAPI) -> None:
    _remove_route_if_present(app, INCOMING_ROUTE_PATH)

    async def handle_incoming_call(request: Request):
        return Response(
            content=_build_language_gather_twiml(request),
            media_type="application/xml",
        )

    app.add_api_route(
        INCOMING_ROUTE_PATH,
        handle_incoming_call,
        methods=["GET", "POST"],
        include_in_schema=False,
    )


def _replace_telephone_language_route(app: FastAPI) -> None:
    _remove_route_if_present(app, LANGUAGE_ROUTE_PATH)

    async def handle_language_selection(request: Request):
        form = await request.form()
        retry_count = _coerce_retry_count(request.query_params.get("retry"))
        selected_language = _select_language(
            digits=str(form.get("Digits") or ""),
            speech_result=str(form.get("SpeechResult") or ""),
        )

        if selected_language == "english":
            return Response(
                content=_build_connect_twiml(
                    request,
                    voice_path="/voice-en",
                    greeting=ENGLISH_GREETING,
                    language="en-US",
                ),
                media_type="application/xml",
            )
        if selected_language == "spanish":
            return Response(
                content=_build_connect_twiml(
                    request,
                    voice_path="/voice-es",
                    greeting=SPANISH_GREETING,
                    language="es-ES",
                ),
                media_type="application/xml",
            )

        if retry_count + 1 <= settings.call_flow.selection_retry_limit:
            return Response(
                content=_build_language_gather_twiml(
                    request,
                    retry_count=retry_count + 1,
                ),
                media_type="application/xml",
            )

        logger.info("Telephone language selection exhausted. Defaulting to Spanish.")
        return Response(
            content=_build_connect_twiml(
                request,
                voice_path="/voice-es",
                greeting=SPANISH_SELECTION_FALLBACK,
                language="es-ES",
            ),
            media_type="application/xml",
        )

    app.add_api_route(
        LANGUAGE_ROUTE_PATH,
        handle_language_selection,
        methods=["POST"],
        include_in_schema=False,
    )


def mount_voice_stream(app: FastAPI):
    """
    Mount the FastRTC voice streams to the application.

    `/voice` remains the generic route for local/WebRTC usage.
    `/voice-es` and `/voice-en` provide dedicated telephone handlers.
    """
    try:
        generic_agent = FastRTCAgent(
            thread_id=str(uuid4()),
        )
        english_agent = FastRTCAgent(
            thread_id=str(uuid4()),
            language_locked="english",
            can_interrupt=True,
        )
        spanish_tts_model = get_tts_model("elevenlabs-es")
        spanish_agent = FastRTCAgent(
            thread_id=str(uuid4()),
            spanish_tts_model=spanish_tts_model,
            language_locked="spanish",
            can_interrupt=True,
        )

        generic_agent.stream.mount(app, path="/voice")
        english_agent.stream.mount(app, path="/voice-en")
        spanish_agent.stream.mount(app, path="/voice-es")
        _replace_telephone_incoming_route(app)
        _replace_telephone_language_route(app)

        app.state.voice_agents = {
            "default": generic_agent,
            "english": english_agent,
            "spanish": spanish_agent,
        }
        app.state.voice_stream_available = True
        app.state.voice_stream_error = None
    except Exception as exc:
        app.state.voice_stream_available = False
        app.state.voice_stream_error = str(exc)
        logger.warning(
            f"Voice stream was not mounted. HTTP knowledge routes remain available. Error: {exc}"
        )
