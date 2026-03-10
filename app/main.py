from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.relivio import ingest_unhandled_error

load_dotenv()

app = FastAPI(title="Relivio FastAPI Example")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo/ok")
async def demo_ok() -> dict[str, str]:
    return {"status": "ok", "message": "No error raised."}


@app.get("/demo/fail")
async def demo_fail() -> dict[str, str]:
    raise RuntimeError("checkout failed: payment replica unavailable")


@app.get("/demo/fail-timeout")
async def demo_fail_timeout() -> dict[str, str]:
    raise TimeoutError("checkout timeout while waiting for downstream inventory")


@app.get("/demo/fail-validation")
async def demo_fail_validation() -> dict[str, str]:
    raise ValueError("checkout payload validation failed: currency code missing")


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
