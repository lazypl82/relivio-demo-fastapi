from __future__ import annotations

import argparse

from demo_lib import load_demo_config, print_recent_deployments
from mcp_lib import list_recent_deployments_via_mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List recent deployments through relivio-mcp for the configured Relivio project."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="How many recent deployments to fetch.",
    )
    args = parser.parse_args()

    config = load_demo_config()
    items = list_recent_deployments_via_mcp(
        api_url=config.relivio_api_base_url,
        api_key=config.relivio_project_api_key,
        limit=args.limit,
    )
    print_recent_deployments(items)


if __name__ == "__main__":
    main()
