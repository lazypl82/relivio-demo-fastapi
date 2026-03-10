from __future__ import annotations

import argparse
import os
from pprint import pprint

import httpx
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the latest Relivio summary.")
    parser.add_argument("--deployment-id", help="Deployment id to filter latest summary.")
    args = parser.parse_args()

    load_dotenv()

    api_base_url = os.environ["RELIVIO_API_BASE_URL"]
    api_key = os.environ["RELIVIO_PROJECT_API_KEY"]

    params = {}
    if args.deployment_id:
        params["deployment_id"] = args.deployment_id

    response = httpx.get(
        f"{api_base_url}/api/v1/summaries/latest",
        headers={"X-API-Key": api_key},
        params=params,
        timeout=5.0,
    )

    if response.status_code == 404:
        print(response.text)
        return

    response.raise_for_status()
    payload = response.json()

    print(f"verdict={payload.get('verdict')}")
    print(f"score={payload.get('score')}")
    print(f"recommended_action={payload.get('recommended_action')}")
    print(f"recommended_action_detail={payload.get('recommended_action_detail')}")
    print(f"affected_apis={payload.get('affected_apis')}")

    guidance = payload.get("protection_guidance")
    if guidance:
        print("protection_guidance:")
        pprint(guidance)


if __name__ == "__main__":
    main()
