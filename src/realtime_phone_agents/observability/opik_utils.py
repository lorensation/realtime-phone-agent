from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from loguru import logger

from realtime_phone_agents.config import settings

try:
    import opik
    from opik.integrations.langchain import OpikTracer
except ImportError:  # pragma: no cover - exercised via runtime environment
    opik = None
    OpikTracer = None


def is_opik_enabled() -> bool:
    return bool(opik is not None and settings.opik.api_key)


def configure() -> bool:
    """Configure the Opik SDK from application settings."""
    if opik is None:
        logger.info("Opik SDK is not installed. Prompt versioning and tracing disabled.")
        return False

    if not settings.opik.api_key:
        logger.info("Opik disabled. Missing OPIK__API_KEY.")
        return False

    os.environ["OPIK_API_KEY"] = settings.opik.api_key
    if settings.opik.project_name:
        os.environ["OPIK_PROJECT_NAME"] = settings.opik.project_name

    try:
        opik.configure(
            api_key=settings.opik.api_key,
            use_local=False,
            force=True,
            automatic_approvals=True,
        )
        logger.info(
            "Opik configured for project '{}'.",
            settings.opik.project_name or "<default>",
        )
        return True
    except Exception as exc:  # pragma: no cover - depends on external service
        logger.warning(f"Failed to configure Opik: {exc}")
        return False


def build_langchain_callbacks(
    *,
    thread_id: str,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[Any]:
    """Create LangChain callbacks for Opik tracing when configured."""
    if not is_opik_enabled() or OpikTracer is None:
        return []

    try:
        tracer = OpikTracer(
            project_name=settings.opik.project_name or None,
            thread_id=thread_id,
            tags=tags or None,
            metadata=metadata or None,
        )
    except Exception as exc:  # pragma: no cover - depends on external service
        logger.warning(f"Failed to initialize Opik tracer: {exc}")
        return []

    return [tracer]


def track(
    name: str,
    *,
    type: str = "general",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    capture_input: bool = True,
    ignore_arguments: list[str] | None = None,
    capture_output: bool = True,
    flush: bool = False,
    entrypoint: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Return an Opik tracking decorator with a safe local fallback."""

    def noop_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    if opik is None:
        return noop_decorator

    return opik.track(
        name=name,
        type=type,
        tags=tags,
        metadata=metadata,
        capture_input=capture_input,
        ignore_arguments=ignore_arguments,
        capture_output=capture_output,
        flush=flush,
        project_name=settings.opik.project_name or None,
        entrypoint=entrypoint,
    )
