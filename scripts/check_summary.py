from __future__ import annotations

import argparse
import os
import time
from pprint import pprint

import httpx
from dotenv import load_dotenv


def print_summary(payload: dict[str, object]) -> None:
    print(f"verdict={payload.get('verdict')}")
    print(f"score={payload.get('score')}")
    print(f"recommended_action={payload.get('recommended_action')}")
    print(f"recommended_action_detail={payload.get('recommended_action_detail')}")
    print(f"affected_apis={payload.get('affected_apis')}")

    guidance = payload.get("protection_guidance")
    if guidance:
        print("protection_guidance:")
        pprint(guidance)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the latest Relivio summary.")
    parser.add_argument("--deployment-id", help="Deployment id to filter latest summary.")
    parser.add_argument("--wait", action="store_true", help="Poll until the summary is ready.")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=15.0,
        help="Polling interval used with --wait.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=960.0,
        help="Maximum wait time used with --wait.",
    )
    args = parser.parse_args()

    load_dotenv()

    api_base_url = os.environ["RELIVIO_API_BASE_URL"]
    api_key = os.environ["RELIVIO_PROJECT_API_KEY"]

    params = {}
    if args.deployment_id:
        params["deployment_id"] = args.deployment_id

    deadline = time.monotonic() + max(args.timeout_seconds, 0.0)

    while True:
        response = httpx.get(
            f"{api_base_url}/api/v1/summaries/latest",
            headers={"X-API-Key": api_key},
            params=params,
            timeout=5.0,
        )

        if response.status_code != 404:
            response.raise_for_status()
            print_summary(response.json())
            return

        if not args.wait:
            print(response.text)
            return

        if time.monotonic() >= deadline:
            print("Timed out waiting for the summary.")
            print(response.text)
            return

        print(
            f"Summary not ready yet. Waiting {args.interval_seconds:g}s before checking again..."
        )
        time.sleep(max(args.interval_seconds, 0.5))


if __name__ == "__main__":
    main()
