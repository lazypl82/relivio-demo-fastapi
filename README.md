# relivio-demo-fastapi

Minimal FastAPI demo for seeing Relivio wired into a backend in a few minutes.

`register deploy with SDK -> trigger failures -> read verdict through MCP`

This repo is intentionally small. Its job is simple:

`show the shortest backend path that produces a real Relivio decision`

What this demo gives you:

1. A minimal FastAPI app with one shared error middleware.
2. A concrete `deployment -> ingest -> verdict` flow using the current public surfaces.
3. A small codebase you can compare against your own service.
4. A one-shot demo script that runs the full SDK + MCP path end to end.
5. A small MCP read path so you can recover the newest `deployment_id` without copying it around manually.

## Fastest path

If you only want the shortest working demo, use this path:

```bash
source .venv/bin/activate
python scripts/doctor.py
python scripts/trigger_failure.py --list-scenarios
python scripts/demo_agent_cycle.py --scenario risk-demo
```

Expected result:

- doctor confirms local app + Relivio runtime auth are ready
- deployment registration happens automatically
- the demo app triggers a scenario shaped for `STABLE`, `WATCH`, or `RISK`
- the script waits through MCP and prints the final verdict
- `deploy_ack` is sent first
- `summary_final` appears after the observation window closes
- the mixed `risk` scenario surfaces a stronger signal than one repeated error
- final verdict can still vary depending on the signals right before the deploy and your current Relivio scoring model

## 1. Setup

```bash
cd relivio-demo-fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g relivio-mcp@0.2.0
cp .env.example .env
```

Fill in `.env` with:

- `RELIVIO_API_BASE_URL`
- `RELIVIO_PROJECT_API_KEY`
- `RELIVIO_SERVICE_NAME` (optional, default is `relivio-demo-fastapi`)
- `APP_BASE_URL` (optional, default is fine)
- `RELIVIO_MCP_COMMAND` (optional, default is `relivio-mcp`)

## 2. Run the app

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Scenario catalog:

```bash
curl http://127.0.0.1:8000/demo/scenarios
```

Optional readiness check:

```bash
source .venv/bin/activate
python scripts/doctor.py
```

## 3. Register a deployment

```bash
source .venv/bin/activate
python scripts/register_deploy.py
```

Example output:

```text
deployment_id=0195f8d8-6f3c-7d4c-bd79-8a0ab2d2a911
version=relivio-demo-20260310121500
summary_note=In the hosted environment, the summary is usually ready after the observation window closes.
```

Current default marker shape:

- `version`: `relivio-demo-<timestamp>`
- deployment metadata:
  - `source=relivio-demo-fastapi`
  - `environment=demo`
  - `demo_flow=true`
- log `service`: `relivio-demo-fastapi`

These markers make demo runs easier to identify and exclude later from tuning or governance exports.

If you want to confirm what the target project has seen most recently from the agent side:

```bash
source .venv/bin/activate
python scripts/list_recent_deployments.py
```

That uses the runtime read surface:

- `relivio-mcp`
- `list_recent_deployments`
- project-scoped recent deployments only

## 4. Trigger a scenario

One request is enough for a wiring check.
For a more convincing demo, inspect the scenario catalog first, then use one of the shaped scenarios below.

List the available scenarios from the terminal:

```bash
source .venv/bin/activate
python scripts/trigger_failure.py --list-scenarios
```

Or inspect them from the app:

```bash
curl http://127.0.0.1:8000/demo/scenarios
```

```bash
curl http://127.0.0.1:8000/demo/profile/transient-warning
```

Or:

```bash
source .venv/bin/activate
python scripts/trigger_failure.py --scenario watch-demo
```

Current scenario presets:

- `stable-demo`
  - one transient warning on `/api/profile/update`
  - intended to feel like "keep observing"
- `watch-demo`
  - warnings and errors concentrated on `/api/orders/{order_id}/commit`
  - intended to feel like "guard-ready, not rollback-grade"
- `risk-demo`
  - errors spread across checkout and payments routes
  - intended to feel like broader rollback-grade risk

Demo routes used under the hood:

- `/demo/profile/transient-warning`
- `/demo/orders/guard-warning`
- `/demo/orders/guard-error`
- `/demo/checkout/submit-error`
- `/demo/checkout/status-error`
- `/demo/payments/capture-error`

Warnings are sent directly to Relivio with a production-like `api_path`.
Unhandled errors still pass through one shared FastAPI middleware, which sends `POST /api/v1/ingest/log` to Relivio.

Important details:

- `api_path` is sent as a production-like route template such as `/api/orders/{order_id}/commit`.
- the helper script sends a unique `x-request-id` per request
- repeated demo failures are therefore not collapsed by the idempotency key
- `GET /demo/scenarios/{scenario}` returns one scenario definition for quick inspection

## 5. Read the verdict

Agent-side read path through MCP:

```bash
source .venv/bin/activate
python scripts/check_verdict_via_mcp.py --latest-deployment --wait
```

That flow resolves the newest deployment id through MCP, then keeps polling `get_verdict` until the observation window closes.

If you want the lower-level runtime summary directly:

```bash
source .venv/bin/activate
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID> --wait
```

If you do not want to copy the id manually on the direct runtime path:

```bash
source .venv/bin/activate
python scripts/check_summary.py --latest-deployment --wait
```

In the hosted environment, `404 SUMMARY_NOT_READY` is normal until the observation window ends.
Use `--wait` to poll automatically until the summary is ready.

What the summary script prints:

- `verdict`
- `decision_tier`
- `score`
- `recommended_action`
- `recommended_action_detail`
- `affected_apis`
- a short `content_preview`

## One-shot demo

If you want the full backend demo on the current public surfaces without copying `deployment_id` between commands:

```bash
source .venv/bin/activate
python scripts/demo_agent_cycle.py --scenario risk-demo
```

What it does:

1. checks local app health
2. probes the SDK runtime path with your API key
3. registers a deployment through `relivio-sdk-python`
4. prints the selected scenario intent, then triggers the shaped stable/watch/risk sequence
5. resolves the newest deployment through `relivio-mcp`
6. waits for the verdict through `relivio-mcp`, then prints the verdict + decision tier

## What this repo demonstrates

- `relivio-sdk-python` is used for deployment registration
- `relivio-sdk-python` is used in the FastAPI middleware for ingest
- `relivio-mcp` is used to list recent deployments and read deploy verdicts
- `python scripts/demo_agent_cycle.py` stitches the full SDK + MCP path together for demo use
- `python scripts/list_recent_deployments.py` reads the newest project-scoped deployment ids through MCP
- `python scripts/check_verdict_via_mcp.py --latest-deployment --wait` reads the newest deployment verdict through MCP
- `python scripts/check_summary.py --latest-deployment --wait` remains as a lower-level runtime summary inspection path

This repo is not a production starter kit.
It is a minimal, concrete backend example that still produces a real Relivio decision.

Because this demo uses the real runtime path, each run persists deployment, ingest, and summary records in the target Relivio project. Use a dedicated demo project or API key, not a project you plan to treat as clean learning data later.

This repo still treats deploy registration as a deploy-boundary action.
It does not register deployments from app startup hooks.
The server-side multi-worker dedup path is a safety net, not the preferred integration shape.

## Start here

If you only want the integration shape, start here:

- [app/main.py](./app/main.py)
- [app/relivio.py](./app/relivio.py)

For a first rollout, those two files are enough to understand the integration shape.

## Local routes

- `GET /`
- `GET /health`
- `GET /demo/scenarios`
- `GET /demo/scenarios/{scenario}`
- `GET /demo/ok`
- `GET /demo/profile/transient-warning`
- `GET /demo/orders/guard-warning`
- `GET /demo/orders/guard-error`
- `GET /demo/checkout/submit-error`
- `GET /demo/checkout/status-error`
- `GET /demo/payments/capture-error`
- `GET /demo/fail`
- `GET /demo/fail-timeout`
- `GET /demo/fail-validation`
