# relivio-demo-fastapi

Minimal FastAPI demo for seeing Relivio wired into a backend in a few minutes.

`register deploy -> trigger failures -> read verdict`

This repo is intentionally small. Its job is simple:

`show the shortest backend path that produces a real Relivio decision`

What this demo gives you:

1. A minimal FastAPI app with one shared error middleware.
2. A concrete `deployment -> ingest -> summary` flow.
3. A small codebase you can compare against your own service.
4. A one-shot demo script that runs the full path end to end.

## Fastest path

If you only want the shortest working demo, use this path:

```bash
source .venv/bin/activate
python scripts/doctor.py
python scripts/demo_flow.py --scenario risk-demo
```

Expected result:

- doctor confirms local app + Relivio runtime auth are ready
- deployment registration happens automatically
- the demo app triggers a scenario shaped for `STABLE`, `WATCH`, or `RISK`
- the script waits for the summary and prints the final verdict
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
cp .env.example .env
```

Fill in `.env` with:

- `RELIVIO_API_BASE_URL`
- `RELIVIO_PROJECT_API_KEY`
- `RELIVIO_SERVICE_NAME` (optional, default is `relivio-demo-fastapi`)
- `APP_BASE_URL` (optional, default is fine)

## 2. Run the app

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
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

## 4. Trigger a scenario

One request is enough for a wiring check.
For a more convincing demo, use one of the shaped scenarios below.

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

## 5. Read the verdict

```bash
source .venv/bin/activate
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID> --wait
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

If you want the full backend demo without copying `deployment_id` between commands:

```bash
source .venv/bin/activate
python scripts/demo_flow.py --scenario risk-demo
```

What it does:

1. checks local app health
2. probes Relivio runtime auth with your API key
3. registers a deployment
4. triggers a shaped stable/watch/risk scenario across multiple demo routes
5. waits for the summary, prints retry progress, then prints the verdict + decision tier

## What this repo demonstrates

- `POST /api/v1/deployments` is called by a script
- `POST /api/v1/ingest/log` is called by FastAPI middleware
- `GET /api/v1/summaries/latest` is called by a lookup script
- `python scripts/demo_flow.py` stitches the whole path together for demo use

This repo is not a production starter kit.
It is a minimal, concrete backend example that still produces a real Relivio decision.

Because this demo uses the real runtime path, each run persists deployment, ingest, and summary records in the target Relivio project. Use a dedicated demo project or API key, not a project you plan to treat as clean learning data later.

## Start here

If you only want the integration shape, start here:

- [app/main.py](./app/main.py)
- [app/relivio.py](./app/relivio.py)

For a first rollout, those two files are enough to understand the integration shape.

## Local routes

- `GET /health`
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
