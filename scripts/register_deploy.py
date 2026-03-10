from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a deployment with Relivio.")
    parser.add_argument("--version", help="Deployment version label.")
    parser.add_argument("--note", default="fastapi example deploy", help="Optional deployment note.")
    args = parser.parse_args()

    load_dotenv()

    api_base_url = os.environ["RELIVIO_API_BASE_URL"]
    api_key = os.environ["RELIVIO_PROJECT_API_KEY"]
    version = args.version or f"example-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    idempotency_key = f"deploy:{version}"

    response = httpx.post(
        f"{api_base_url}/api/v1/deployments",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "Idempotency-Key": idempotency_key,
        },
        json={
            "version": version,
            "note": args.note,
            "metadata": {
                "source": "relivio-demo-fastapi",
                "environment": "demo",
            },
        },
        timeout=5.0,
    )
    response.raise_for_status()
    payload = response.json()
    deployment_id = payload.get("id") or payload.get("deployment_id")

    if not deployment_id:
        raise RuntimeError(f"deployment id missing in response: {payload}")

    print(f"deployment_id={deployment_id}")
    print(f"version={version}")
    print("summary_note=In the hosted environment, the summary is usually ready after the observation window closes.")
    print("next:")
    print("  1) Trigger an error: curl http://127.0.0.1:8000/demo/fail")
    print(
        f"  2) Wait for the verdict: python scripts/check_summary.py --deployment-id {deployment_id} --wait"
    )


if __name__ == "__main__":
    main()
