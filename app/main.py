from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.relivio_setup import relivio, request_id_var
from app.routes import router as demo_router

app = FastAPI(title="Relivio FastAPI Example")


def resolve_api_path(scope: Scope) -> str:
    state = scope.get("state")
    overridden = state.get("relivio_api_path_override") if isinstance(state, dict) else None
    if isinstance(overridden, str) and overridden.strip():
        return overridden.strip()
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    path = scope.get("path")
    return str(path or "")


class RelivioDemoMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        request_id = headers.get(b"x-request-id")
        token = request_id_var.set(request_id.decode("latin-1") if request_id else None)
        response_started = False

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            await relivio.acapture_exception(exc, api_path=resolve_api_path(scope))
            if response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                },
            )
            await response(scope, receive, send)
        finally:
            request_id_var.reset(token)


app.add_middleware(RelivioDemoMiddleware)
app.include_router(demo_router)
