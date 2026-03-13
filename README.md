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
- the demo app triggers failures across multiple routes
- the script waits for the summary and prints the final verdict
- `deploy_ack` is sent first
- `summary_final` appears after the observation window closes
- the mixed `risk` scenario surfaces a stronger signal than one repeated error
- final verdict can still vary depending on your current Relivio baseline and scoring model

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
- `RELIVIO_SERVICE_NAME` (optional, default is fine)
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
version=example-20260310121500
summary_note=In the hosted environment, the summary is usually ready after the observation window closes.
```

## 4. Trigger failures

One request is enough for a wiring check.
For a stronger demo, use the mixed `risk` scenario so Relivio sees multiple failing fingerprints instead of one repeated error.

```bash
curl http://127.0.0.1:8000/demo/fail
```

Or:

```bash
source .venv/bin/activate
python scripts/trigger_failure.py --scenario risk-demo
```

That path cycles through:

- `/demo/fail`
- `/demo/fail-timeout`
- `/demo/fail-validation`

These requests pass through one shared FastAPI error middleware, which sends `POST /api/v1/ingest/log` to Relivio.

Important details:

- `api_path` is sent using the matched route template.
- the helper script sends a unique `x-request-id` per request
- repeated demo failures are therefore not collapsed by the idempotency key

## 5. Read the verdict

```bash
source .venv/bin/activate
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID> --wait
```

In the hosted environment, `404 SUMMARY_NOT_READY` is normal until the observation window ends.
Use `--wait` to poll automatically until the summary is ready.

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
4. triggers failing requests across multiple demo routes
5. waits for the summary and prints the verdict

## What this repo demonstrates

- `POST /api/v1/deployments` is called by a script
- `POST /api/v1/ingest/log` is called by FastAPI middleware
- `GET /api/v1/summaries/latest` is called by a lookup script
- `python scripts/demo_flow.py` stitches the whole path together for demo use

This repo is not a production starter kit.
It is a minimal, concrete backend example that still produces a real Relivio decision.

## Start here

If you only want the integration shape, start here:

- [app/main.py](./app/main.py)
- [app/relivio.py](./app/relivio.py)

For a first rollout, those two files are enough to understand the integration shape.

## Local routes

- `GET /health`
- `GET /demo/ok`
- `GET /demo/fail`
- `GET /demo/fail-timeout`
- `GET /demo/fail-validation`
