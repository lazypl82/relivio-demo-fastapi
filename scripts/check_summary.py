from __future__ import annotations

import argparse
import time

from demo_lib import (
    fetch_provisional_summary,
    fetch_summary,
    load_demo_config,
    print_provisional_summary,
    print_summary,
    resolve_latest_deployment_id,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the latest Relivio summary.")
    parser.add_argument("--deployment-id", help="Deployment id to filter latest summary.")
    parser.add_argument(
        "--provisional",
        action="store_true",
        help="Read the active deploy-window provisional summary instead of the final summary.",
    )
    parser.add_argument(
        "--latest-deployment",
        action="store_true",
        help="Resolve the most recent deployment id first, then read its summary.",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=5,
        help="How many recent deployments to inspect when --latest-deployment is used.",
    )
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

    config = load_demo_config()
    deployment_id = args.deployment_id

    if args.latest_deployment:
        if deployment_id:
            raise SystemExit("Use either --deployment-id or --latest-deployment, not both.")
        deployment_id = resolve_latest_deployment_id(config, limit=args.recent_limit)
        if not deployment_id:
            raise SystemExit("No recent deployment id found for this project.")
        print(f"selected_deployment_id={deployment_id}")

    deadline = time.monotonic() + max(args.timeout_seconds, 0.0)

    while True:
        if args.provisional:
            response = fetch_provisional_summary(config, deployment_id=deployment_id)
        else:
            response = fetch_summary(config, deployment_id=deployment_id)

        if response.status_code != 404:
            response.raise_for_status()
            if args.provisional:
                print_provisional_summary(response.json())
            else:
                print_summary(response.json())
            return

        if not args.wait:
            print(response.text)
            return

        if time.monotonic() >= deadline:
            label = "provisional summary" if args.provisional else "summary"
            print(f"Timed out waiting for the {label}.")
            print(response.text)
            return

        label = "Provisional summary" if args.provisional else "Summary"
        print(f"{label} not ready yet. Waiting {args.interval_seconds:g}s before checking again...")
        time.sleep(max(args.interval_seconds, 0.5))


if __name__ == "__main__":
    main()
