from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from realtime_phone_agents.infrastructure.superlinked.service import (
    get_knowledge_search_service,
)
from realtime_phone_agents.api.routes import health, knowledge, superlinked
from realtime_phone_agents.api.routes.voice import mount_voice_stream
from realtime_phone_agents.observability.opik_utils import (
    configure as configure_opik,
    track as track_with_opik,
)


@track_with_opik(
    name="app.initialize_services",
    tags=["app", "startup"],
    ignore_arguments=["app"],
    capture_output=False,
    entrypoint=True,
)
async def initialize_services(app: FastAPI) -> None:
    """Initialize shared application services."""
    app.state.knowledge_service = get_knowledge_search_service()


@track_with_opik(
    name="app.shutdown_services",
    tags=["app", "shutdown"],
    ignore_arguments=["app"],
    capture_output=False,
)
async def shutdown_services(app: FastAPI) -> None:
    """Application shutdown hook."""
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events."""
    configure_opik()
    await initialize_services(app)
    yield
    await shutdown_services(app)


app = FastAPI(
    title="Blue Sardine Hotel Assistant API",
    description="An AI-powered hotel assistant API using FastRTC and Superlinked",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(knowledge.router)
app.include_router(superlinked.router)

# Mount voice stream for Twilio integration
mount_voice_stream(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
