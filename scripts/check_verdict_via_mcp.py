from __future__ import annotations

import argparse
import time

from demo_lib import load_demo_config
from mcp_lib import get_verdict_via_mcp, list_recent_deployments_via_mcp


def print_verdict(payload: dict[str, object]) -> None:
    status = payload.get("status")
    print(f"status={status}")

    if status == "ready":
        verdict = payload.get("verdict")
        if not isinstance(verdict, dict):
            raise SystemExit(f"Invalid verdict payload: {payload}")
        print(f"deployment_id={verdict.get('deployment_id')}")
        print(f"verdict={verdict.get('verdict')}")
        print(f"decision_tier={verdict.get('decision_tier')}")
        print(f"recommended_action={verdict.get('recommended_action')}")
        print(f"action_detail={verdict.get('action_detail')}")
        print(f"affected_apis={verdict.get('affected_apis')}")
        print(f"top_signals={verdict.get('top_signals')}")
        print(f"created_at={verdict.get('created_at')}")
        return

    print(f"reason={payload.get('reason')}")
    print(f"message={payload.get('message')}")
    retry_hint = payload.get("retry_after_hint_minutes")
    if retry_hint is not None:
        print(f"retry_after_hint_minutes={retry_hint}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read the deploy verdict through relivio-mcp."
    )
    parser.add_argument("--deployment-id", help="Deployment id to query through MCP.")
    parser.add_argument(
        "--latest-deployment",
        action="store_true",
        help="Resolve the newest deployment id through MCP first, then query its verdict.",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=5,
        help="How many recent deployments to inspect when --latest-deployment is used.",
    )
    parser.add_argument("--wait", action="store_true", help="Poll MCP until the verdict is ready.")
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

    if args.deployment_id and args.latest_deployment:
        raise SystemExit("Use either --deployment-id or --latest-deployment, not both.")

    config = load_demo_config()
    deployment_id = args.deployment_id

    if args.latest_deployment:
        items = list_recent_deployments_via_mcp(
            api_url=config.relivio_api_base_url,
            api_key=config.relivio_project_api_key,
            limit=args.recent_limit,
        )
        if not items:
            raise SystemExit("No recent deployment id found for this project.")
        latest = items[0]
        deployment_id = str(latest["deployment_id"])
        print(f"selected_deployment_id={deployment_id}")

    deadline = time.monotonic() + max(args.timeout_seconds, 0.0)

    while True:
        result = get_verdict_via_mcp(
            api_url=config.relivio_api_base_url,
            api_key=config.relivio_project_api_key,
            deployment_id=deployment_id,
        )

        if result.get("status") != "pending":
            print_verdict(result)
            return

        if not args.wait:
            print_verdict(result)
            return

        if time.monotonic() >= deadline:
            print("Timed out waiting for the verdict.")
            print_verdict(result)
            return

        print(
            f"Verdict not ready yet. Waiting {args.interval_seconds:g}s before checking again..."
        )
        time.sleep(max(args.interval_seconds, 0.5))


if __name__ == "__main__":
    main()
