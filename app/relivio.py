from __future__ import annotations

import os
import traceback
import uuid
from dataclasses import dataclass

from fastapi import Request
from relivio import IngestLogInput, Relivio


@dataclass(frozen=True)
class RelivioConfig:
    api_base_url: str
    api_key: str
    service_name: str


def load_relivio_config() -> RelivioConfig:
    api_base_url = os.environ["RELIVIO_API_BASE_URL"]
    api_key = os.environ["RELIVIO_PROJECT_API_KEY"]
    service_name = os.getenv("RELIVIO_SERVICE_NAME", "relivio-demo-fastapi")
    return RelivioConfig(
        api_base_url=api_base_url,
        api_key=api_key,
        service_name=service_name,
    )


def resolve_api_path(request: Request) -> str:
    overridden = getattr(request.state, "relivio_api_path_override", None)
    if isinstance(overridden, str) and overridden.strip():
        return overridden.strip()
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    return request.url.path


def build_idempotency_key(request_id: str, api_path: str, error_type: str) -> str:
    return f"log:{request_id}:{api_path}:{error_type}"


def build_relivio_client(config: RelivioConfig) -> Relivio:
    return Relivio(
        api_key=config.api_key,
        base_url=config.api_base_url,
    )


async def emit_demo_signal(
    request: Request,
    *,
    level: str,
    message: str,
    error_type: str,
    api_path: str,
    stacktrace: str | None = None,
) -> None:
    config = load_relivio_config()
    request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex}"
    client = build_relivio_client(config)
    await client.ingest.asend(
        IngestLogInput(
            level=level,
            message=message,
            service=config.service_name,
            api_path=api_path,
            stacktrace=stacktrace,
            trace_id=request_id,
            error_type=error_type,
            idempotency_key=build_idempotency_key(request_id, api_path, error_type),
        )
    )


async def ingest_unhandled_error(request: Request, exc: Exception) -> None:
    error_type = exc.__class__.__name__
    stacktrace = "\n".join(traceback.format_exception(exc))[:4000]
    await emit_demo_signal(
        request,
        level="ERROR",
        message=str(exc) or "Unhandled backend error",
        error_type=error_type,
        api_path=resolve_api_path(request),
        stacktrace=stacktrace,
    )
