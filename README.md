# relivio-demo-fastapi

Minimal FastAPI service that shows how Relivio turns post-deploy runtime errors into a deployment verdict such as `STABLE`, `WATCH`, or `RISK`.

This repo demonstrates the client-service side of a Relivio integration:

`register deployment with SDK -> emit post-deploy signals with SDK -> wait for the observation window -> inspect the verdict from notification/MCP/fallback summary -> start with the affected API -> leave feedback when useful`

It intentionally does not call MCP from inside the demo app. MCP is an agent/client consumption path, not an application runtime dependency.

## Fast Path

Use this when you want to see the full deploy-to-verdict loop quickly.

```bash
git clone https://github.com/lazypl82/relivio-demo-fastapi.git
cd relivio-demo-fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with a Relivio project runtime API key:

```dotenv
RELIVIO_API_BASE_URL=https://api.relivio.dev
RELIVIO_PROJECT_API_KEY=<PROJECT_RUNTIME_API_KEY>
RELIVIO_SERVICE_NAME=relivio-demo-fastapi
APP_BASE_URL=http://127.0.0.1:8000
```

Run the local app:

```bash
uvicorn app.main:app --reload
```

In another terminal, emit the representative demo scenario:

```bash
source .venv/bin/activate
python scripts/doctor.py
python scripts/run_demo.py --scenario watch-demo
```

Example run output:

```text
Relivio FastAPI SDK demo
scenario: watch-demo | intended_outcome=rollback-ready WATCH | default_count=15
1/4 app health: OK - local demo app responded to /health
2/4 Relivio API probe: OK - Relivio runtime probe reached the project-scoped verdict surface
3/4 deployment registered via SDK: deployment_id=dep_... version=relivio-demo-...
4/4 scenario emitted through local FastAPI app: scenario=watch-demo count=15 signals=checkout-status-error, checkout-submit-error, payment-capture-error
   trigger_statuses: 500x15

Next:
- Wait for the observation window to close.
- Ask your MCP-enabled agent to inspect this deployment through Relivio.
- Start with the first affected API from the verdict before broad debugging.
- Leave feedback/correction if the verdict was wrong, useful, or led to rollback.
- deployment_id=dep_...
- If you need a raw HTTP fallback: python scripts/check_summary.py --deployment-id dep_... --wait
```

After the observation window closes, inspect the verdict:

```bash
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID> --wait
```

Example verdict output:

```text
verdict=WATCH
decision_tier=rollback_ready
score=49
recommended_action=Inspect checkout now and keep rollback ready
recommended_action_detail=Start with /api/checkout/submit. Prepare a narrow containment path if the same signal continues into the next observation window.
affected_apis=['/api/checkout/submit', '/api/payments/{payment_id}/capture', '/api/checkout/status']
delivery_status=ready
agent_ready=True
```

The local FastAPI app has no login or paid dependency. The hosted Relivio API call requires a Relivio project runtime API key because the demo writes real deployment, ingest, and summary records.

## What This Shows

- A deploy-boundary `deployment.register` call.
- A FastAPI exception boundary that uses `relivio.acapture_exception(...)`.
- A `trace_id_provider` wired through `ContextVar`.
- A few shaped local signals that push the verdict toward `STABLE`, `WATCH`, or `RISK` after the observation window.
- A raw HTTP fallback script for inspecting the summary if you are not using an MCP-enabled agent.
- The `deployment_id` returned by registration, which is the handle an operator or agent can use to inspect the same deploy later.

## Setup

```bash
cd relivio-demo-fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with:

- `RELIVIO_API_BASE_URL`
- `RELIVIO_PROJECT_API_KEY`
- `RELIVIO_SERVICE_NAME` optional, defaults to `relivio-demo-fastapi`
- `APP_BASE_URL` optional, defaults to `http://127.0.0.1:8000`

## Run The App

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

In another terminal:

```bash
source .venv/bin/activate
python scripts/doctor.py
python scripts/run_demo.py --scenario watch-demo
```

`run_demo.py` performs the application-side flow only:

1. Checks local app health.
2. Probes the Relivio API key.
3. Registers a deployment through the `relivio` Python SDK.
4. Emits the selected scenario through the local FastAPI app.
5. Prints the SDK response `deployment_id` for external inspection.

After the observation window closes, ask your MCP-enabled agent to inspect that deployment through Relivio. If you need a raw fallback:

```bash
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID> --wait
```

The first verdict path is intentionally the same as production:

1. Register deployment at the deploy boundary.
   - The register response returns `deployment_id`; keep it in CI/demo logs when available.
2. Emit runtime errors from the app boundary.
3. Wait for the observation window to close.
4. Read the verdict from notification, MCP, or the fallback summary script.
5. Inspect the first affected API before broad debugging.
6. Leave feedback/correction when the verdict was wrong, useful, or led to rollback.

## Scenarios

```bash
python scripts/run_demo.py --list-scenarios
```

Available presets:

- `single-demo`: one checkout error for the smallest wiring check.
- `stable-demo`: one transient profile warning.
- `contained-demo`: repeated order-route warnings/errors for a smaller guard-style signal.
- `watch-demo`: representative sustained checkout/payment signal that usually lands in WATCH / rollback-ready.

`risk-demo` and `risk` remain accepted as compatibility aliases for `watch-demo`; the public demo intentionally represents WATCH instead of pretending every noisy deployment must become RISK.

The app exposes a compact signal endpoint instead of many route-specific demo endpoints:

```bash
curl http://127.0.0.1:8000/demo/scenarios
curl http://127.0.0.1:8000/demo/signals/checkout-submit-error
curl http://127.0.0.1:8000/demo/signals/profile-warning
```

Error signals intentionally return `500`. The demo script treats those responses as expected signal generation, not as script failure.

## Integration Shape

Start with these files:

- [app/relivio_setup.py](./app/relivio_setup.py)
- [app/main.py](./app/main.py)
- [app/routes.py](./app/routes.py)

`app/relivio_setup.py` creates one SDK client:

```python
relivio = Relivio(
    api_key=os.environ["RELIVIO_PROJECT_API_KEY"],
    base_url=os.environ["RELIVIO_API_BASE_URL"],
    default_service=os.getenv("RELIVIO_SERVICE_NAME", "relivio-demo-fastapi"),
    trace_id_provider=request_id_var.get,
)
```

`app/main.py` keeps exception capture at one ASGI boundary:

```python
try:
    await self.app(scope, receive, send_wrapper)
except Exception as exc:
    await relivio.acapture_exception(exc, api_path=resolve_api_path(scope))
    await JSONResponse(status_code=500, content={...})(scope, receive, send)
```

The ASGI middleware is used deliberately here because this demo intentionally raises `500` responses as signal data. The boundary captures the exception and returns a stable JSON response without letting the original exception leak back to the ASGI server.

## Scripts

- `scripts/doctor.py`: verifies local app and Relivio API readiness.
- `scripts/run_demo.py`: registers one deployment and emits one scenario.
- `scripts/check_summary.py`: raw HTTP fallback for summary/verdict inspection.
- `scripts/demo_lib.py`: shared script helpers.

## Notes

- This repo is not a production starter kit.
- Deploy registration is shown as a deploy-boundary action, not an app startup hook.
- Runtime signals are not given idempotency keys; repeated demo failures should remain visible.
- Use a dedicated demo project/API key. Demo runs persist deployment, ingest, and summary records in the target Relivio project.
