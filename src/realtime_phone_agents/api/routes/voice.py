from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from loguru import logger

from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent
from realtime_phone_agents.agent.stream import VoiceAgentStream

INCOMING_ROUTE_PATH = "/voice/telephone/incoming"


def _remove_route_if_present(app: FastAPI, route_path: str) -> None:
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != route_path
    ]


def _remove_internal_telephone_routes(app: FastAPI) -> None:
    for route_path in (
        "/voice/telephone/language",
        "/voice-en/telephone/incoming",
        "/voice-es/telephone/incoming",
        "/voice-en/telephone/handler",
        "/voice-es/telephone/handler",
    ):
        _remove_route_if_present(app, route_path)


def _replace_telephone_incoming_route(
    app: FastAPI,
    voice_stream: VoiceAgentStream,
) -> None:
    _remove_route_if_present(app, INCOMING_ROUTE_PATH)

    async def handle_incoming_call(request: Request):
        return await voice_stream.handle_incoming_call(request)

    app.add_api_route(
        INCOMING_ROUTE_PATH,
        handle_incoming_call,
        methods=["GET", "POST"],
        include_in_schema=False,
    )


def mount_voice_stream(app: FastAPI) -> None:
    """
    Mount the FastRTC voice stream to the application.

    `/voice` is the single public route family for local/WebRTC and Twilio usage.
    """
    try:
        generic_agent = FastRTCAgent(thread_id=str(uuid4()))

        generic_agent.stream.mount(app, path="/voice")
        _remove_internal_telephone_routes(app)
        _replace_telephone_incoming_route(app, generic_agent.stream)

        app.state.voice_agents = {"default": generic_agent}
        app.state.voice_stream = generic_agent.stream
        app.state.voice_stream_available = True
        app.state.voice_stream_error = None
    except Exception as exc:
        app.state.voice_stream_available = False
        app.state.voice_stream_error = str(exc)
        logger.warning(
            "Voice stream was not mounted. HTTP knowledge routes remain available. "
            f"Error: {exc}"
        )
