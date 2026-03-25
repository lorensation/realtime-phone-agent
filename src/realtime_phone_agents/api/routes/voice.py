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
        "<Say>Connecting to the AI assistant.</Say>"
        f'<Connect><Stream url="{stream_url}" /></Connect>'
        "<Say>The call has been disconnected.</Say>"
        "</Response>"
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

        # Twilio webhooks are often configured with GET. FastRTC mounts a POST-only
        # handler, so we add a compatible GET route that returns the same TwiML.
        @app.get("/voice/telephone/incoming", include_in_schema=False)
        async def handle_incoming_call_get(request: Request):
            return Response(
                content=_build_telephone_twiml(request, "/voice"),
                media_type="application/xml",
            )

        app.state.voice_stream_available = True
        app.state.voice_stream_error = None
    except Exception as exc:
        app.state.voice_stream_available = False
        app.state.voice_stream_error = str(exc)
        logger.warning(
            f"Voice stream was not mounted. HTTP knowledge routes remain available. Error: {exc}"
        )
