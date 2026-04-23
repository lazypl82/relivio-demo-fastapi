from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.relivio import emit_demo_signal, ingest_unhandled_error
from scripts.demo_scenarios import describe_scenarios, get_scenario_definition

load_dotenv()

app = FastAPI(title="Relivio FastAPI Example")


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "service": "relivio-demo-fastapi",
        "status": "ok",
        "quickstart": [
            "GET /health",
            "GET /demo/scenarios",
            "Run python scripts/demo_agent_cycle.py --scenario risk-demo",
        ],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo/scenarios")
async def demo_scenarios() -> dict[str, object]:
    return {
        "count": len(describe_scenarios()),
        "scenarios": describe_scenarios(),
    }


@app.get("/demo/scenarios/{scenario_name}")
async def demo_scenario_detail(scenario_name: str) -> dict[str, object]:
    scenario = get_scenario_definition(scenario_name)
    return scenario.to_dict()


@app.get("/demo/ok")
async def demo_ok() -> dict[str, str]:
    return {"status": "ok", "message": "No error raised."}


@app.get("/demo/profile/transient-warning")
async def demo_profile_transient_warning(request: Request) -> dict[str, str]:
    await emit_demo_signal(
        request,
        level="WARN",
        message="profile update latency spike recovered before escalation",
        error_type="TransientWarning",
        api_path="/api/profile/update",
    )
    return {"status": "accepted", "scenario": "stable-demo", "signal": "warn"}


@app.get("/demo/orders/guard-warning")
async def demo_orders_guard_warning(request: Request) -> dict[str, str]:
    await emit_demo_signal(
        request,
        level="WARN",
        message="order commit retries increased on one route",
        error_type="RouteWarning",
        api_path="/api/orders/{order_id}/commit",
    )
    return {"status": "accepted", "scenario": "watch-demo", "signal": "warn"}


@app.get("/demo/orders/guard-error")
async def demo_orders_guard_error(request: Request) -> dict[str, str]:
    request.state.relivio_api_path_override = "/api/orders/{order_id}/commit"
    raise RuntimeError("order commit failed after earlier route warnings")


@app.get("/demo/checkout/submit-error")
async def demo_checkout_submit_error(request: Request) -> dict[str, str]:
    request.state.relivio_api_path_override = "/api/checkout/submit"
    raise RuntimeError("checkout submit failed: payment replica unavailable")


@app.get("/demo/checkout/status-error")
async def demo_checkout_status_error(request: Request) -> dict[str, str]:
    request.state.relivio_api_path_override = "/api/checkout/status"
    raise TimeoutError("checkout status timed out while waiting for downstream inventory")


@app.get("/demo/payments/capture-error")
async def demo_payments_capture_error(request: Request) -> dict[str, str]:
    request.state.relivio_api_path_override = "/api/payments/{payment_id}/capture"
    raise ValueError("payment capture failed: downstream gateway rejected token")


@app.get("/demo/fail")
async def demo_fail(request: Request) -> dict[str, str]:
    return await demo_checkout_submit_error(request)


@app.get("/demo/fail-timeout")
async def demo_fail_timeout(request: Request) -> dict[str, str]:
    return await demo_checkout_status_error(request)


@app.get("/demo/fail-validation")
async def demo_fail_validation(request: Request) -> dict[str, str]:
    return await demo_payments_capture_error(request)


@app.middleware("http")
async def relivio_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        try:
            await ingest_unhandled_error(request, exc)
        except Exception:
            # Keep the original error flow fail-open if Relivio is unavailable.
            pass
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                }
            },
        )
