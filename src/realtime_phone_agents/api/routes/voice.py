from uuid import uuid4

from fastapi import FastAPI, Request, Response
from loguru import logger

from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent


def _header_value(request: Request, header_name: str, fallback: str) -> str:
    value = request.headers.get(header_name, fallback)
    return value.split(",")[0].strip()


def _build_telephone_twiml(request: Request, voice_path: str) -> str:
    public_host = _header_value(
        request, "x-forwarded-host", request.headers.get("host", "localhost")
    )
    public_scheme = _header_value(request, "x-forwarded-proto", request.url.scheme)
    websocket_scheme = "wss" if public_scheme == "https" else "ws"
    stream_url = f"{websocket_scheme}://{public_host}{voice_path}/telephone/handler"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Connect><Stream url="{stream_url}" /></Connect>'
        "</Response>"
    )


def _replace_telephone_incoming_route(app: FastAPI, voice_path: str) -> None:
    route_path = f"{voice_path}/telephone/incoming"
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != route_path
    ]

    async def handle_incoming_call(request: Request):
        return Response(
            content=_build_telephone_twiml(request, voice_path),
            media_type="application/xml",
        )

    app.add_api_route(
        route_path,
        handle_incoming_call,
        methods=["GET", "POST"],
        include_in_schema=False,
    )


def mount_voice_stream(app: FastAPI):
    """
    Mount the FastRTC agent voice stream to the application.

    Args:
        app: FastAPI application instance
    """
    try:
        agent = FastRTCAgent(
            thread_id=str(uuid4()),
        )

        # Mount Websocket endpoint for Twilio Integration
        agent.stream.mount(app, path="/voice")
        _replace_telephone_incoming_route(app, "/voice")

        app.state.voice_stream_available = True
        app.state.voice_stream_error = None
    except Exception as exc:
        app.state.voice_stream_available = False
        app.state.voice_stream_error = str(exc)
        logger.warning(
            f"Voice stream was not mounted. HTTP knowledge routes remain available. Error: {exc}"
        )
