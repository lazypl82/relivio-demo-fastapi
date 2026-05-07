from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from relivio import IngestLogInput

from app.demo_scenarios import describe_scenarios, get_scenario_definition
from app.relivio_setup import relivio

router = APIRouter()


@dataclass(frozen=True)
class DemoSignal:
    level: str
    message: str
    error_type: str
    api_path: str
    raise_error: Callable[[], Exception] | None = None


SIGNALS: dict[str, DemoSignal] = {
    "profile-warning": DemoSignal(
        level="WARN",
        message="profile update latency spike recovered before escalation",
        error_type="TransientWarning",
        api_path="/api/profile/update",
    ),
    "order-warning": DemoSignal(
        level="WARN",
        message="order commit retries increased on one route",
        error_type="RouteWarning",
        api_path="/api/orders/{order_id}/commit",
    ),
    "order-error": DemoSignal(
        level="ERROR",
        message="order commit failed after earlier route warnings",
        error_type="RuntimeError",
        api_path="/api/orders/{order_id}/commit",
        raise_error=lambda: RuntimeError("order commit failed after earlier route warnings"),
    ),
    "checkout-submit-error": DemoSignal(
        level="ERROR",
        message="checkout submit failed: payment replica unavailable",
        error_type="RuntimeError",
        api_path="/api/checkout/submit",
        raise_error=lambda: RuntimeError("checkout submit failed: payment replica unavailable"),
    ),
    "checkout-status-error": DemoSignal(
        level="ERROR",
        message="checkout status timed out while waiting for downstream inventory",
        error_type="TimeoutError",
        api_path="/api/checkout/status",
        raise_error=lambda: TimeoutError("checkout status timed out while waiting for downstream inventory"),
    ),
    "payment-capture-error": DemoSignal(
        level="ERROR",
        message="payment capture failed: downstream gateway rejected token",
        error_type="ValueError",
        api_path="/api/payments/{payment_id}/capture",
        raise_error=lambda: ValueError("payment capture failed: downstream gateway rejected token"),
    ),
}


async def emit_demo_signal(request: Request, signal: DemoSignal) -> bool:
    try:
        await relivio.ingest.asend(
            IngestLogInput(
                level=signal.level,
                message=signal.message,
                service=os.getenv("RELIVIO_SERVICE_NAME", "relivio-demo-fastapi"),
                api_path=signal.api_path,
                trace_id=request.headers.get("x-request-id"),
                error_type=signal.error_type,
            )
        )
    except Exception:
        return False
    return True


@router.get("/")
async def root() -> dict[str, object]:
    return {
        "service": "relivio-demo-fastapi",
        "status": "ok",
        "quickstart": [
            "GET /health",
            "GET /demo/scenarios",
            "Run python scripts/run_demo.py --scenario risk-demo",
        ],
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/demo/scenarios")
async def demo_scenarios() -> dict[str, object]:
    return {
        "count": len(describe_scenarios()),
        "scenarios": describe_scenarios(),
    }


@router.get("/demo/scenarios/{scenario_name}")
async def demo_scenario_detail(scenario_name: str) -> dict[str, object]:
    scenario = get_scenario_definition(scenario_name)
    return scenario.to_dict()


@router.get("/demo/ok")
async def demo_ok() -> dict[str, str]:
    return {"status": "ok", "message": "No error raised."}


@router.get("/demo/signals/{signal_name}")
async def demo_signal(signal_name: str, request: Request) -> dict[str, str]:
    signal = SIGNALS.get(signal_name)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Unknown demo signal: {signal_name}")

    request.state.relivio_api_path_override = signal.api_path
    if signal.raise_error is not None:
        raise signal.raise_error()

    sent = await emit_demo_signal(request, signal)
    return {
        "status": "accepted",
        "signal": signal_name,
        "api_path": signal.api_path,
        "relivio_ingest": "sent" if sent else "failed",
    }
