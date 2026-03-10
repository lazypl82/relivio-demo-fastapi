# relivio-demo-fastapi

Minimal FastAPI demo for seeing Relivio end-to-end in a few minutes.

`register deploy -> trigger errors -> read verdict`

This repo is intentionally small. It is meant to help you answer one question quickly:

`What does Relivio look like once it is actually wired into a backend?`

It does three things:

1. Shows the exact backend path where Relivio hooks in.
2. Lets you trigger a real failing request and watch the `deploy_ack -> summary_final` flow.
3. Gives you a minimal starting point you can adapt to your own service.

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

## 3. Register a deployment

```bash
source .venv/bin/activate
python scripts/register_deploy.py
```

Example output:

```text
deployment_id=dep_xxxxx
version=example-20260310121500
```

## 4. Trigger failures

One request is enough. Repeated requests make the signal easier to observe.

```bash
curl http://127.0.0.1:8000/demo/fail
```

Or:

```bash
source .venv/bin/activate
python scripts/trigger_failure.py --count 5
```

These requests pass through one shared FastAPI error middleware, which sends `POST /api/v1/ingest/log` to Relivio.
The important part is that `api_path` is sent using the matched route template.

## 5. Read the verdict

```bash
source .venv/bin/activate
python scripts/check_summary.py --deployment-id <DEPLOYMENT_ID>
```

In the hosted environment, `404 SUMMARY_NOT_READY` is normal until the observation window ends.

## What this repo demonstrates

- `POST /api/v1/deployments` is called by a script
- `POST /api/v1/ingest/log` is called by FastAPI middleware
- `GET /api/v1/summaries/latest` is called by a lookup script

This repo is not meant to be a full starter kit.
It is meant to show the concrete code path you add when Relivio is wired into a backend.

## What to look at first

If you only want the integration shape, start here:

- [app/main.py](./app/main.py)
- [app/relivio.py](./app/relivio.py)

For a first rollout, those two files are enough.

## Local routes

- `GET /health`
- `GET /demo/ok`
- `GET /demo/fail`
- `GET /demo/fail-timeout`
