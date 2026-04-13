from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(request: Request):
    """Health and readiness endpoint for deployment checks."""
    voice_ready = bool(getattr(request.app.state, "voice_stream_available", False))
    voice_error = getattr(request.app.state, "voice_stream_error", None)
    knowledge_service = getattr(request.app.state, "knowledge_service", None)
    knowledge_ready = knowledge_service is not None

    healthy = voice_ready and knowledge_ready
    payload = {
        "status": "healthy" if healthy else "unhealthy",
        "message": "Service is ready" if healthy else "Service is not ready",
        "checks": {
            "voice_stream_available": voice_ready,
            "voice_stream_error": voice_error,
            "knowledge_service_available": knowledge_ready,
        },
    }
    return JSONResponse(status_code=200 if healthy else 503, content=payload)
