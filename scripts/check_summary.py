from __future__ import annotations

import argparse
import time

from demo_lib import fetch_summary, load_demo_config, print_summary


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

    config = load_demo_config()

    deadline = time.monotonic() + max(args.timeout_seconds, 0.0)

    while True:
        response = fetch_summary(config, deployment_id=args.deployment_id)

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
