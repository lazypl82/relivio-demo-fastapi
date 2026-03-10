from __future__ import annotations

import argparse
import os
import uuid

import httpx
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger one or more failing requests.")
    parser.add_argument("--path", default="/demo/fail", help="Path to call on the local example app.")
    parser.add_argument("--count", type=int, default=3, help="How many times to call the failing endpoint.")
    parser.add_argument(
        "--scenario",
        choices=("single", "risk"),
        default="single",
        help="Use one path repeatedly or cycle through a stronger risk demo mix.",
    )
    args = parser.parse_args()

    load_dotenv()

    app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    risk_paths = (
        "/demo/fail",
        "/demo/fail-timeout",
        "/demo/fail-validation",
        "/demo/fail",
    )

    with httpx.Client(timeout=3.0) as client:
        for index in range(args.count):
            path = args.path
            if args.scenario == "risk":
                path = risk_paths[index % len(risk_paths)]
            response = client.get(
                f"{app_base_url}{path}",
                headers={"x-request-id": f"demo-{index + 1}-{uuid.uuid4().hex[:12]}"},
            )
            print(f"{index + 1}: path={path} status={response.status_code} body={response.text}")


if __name__ == "__main__":
    main()
