from __future__ import annotations

import argparse

from check_verdict_via_mcp import print_verdict
from demo_lib import (
    check_app_health,
    default_failure_count_for_scenario,
    load_demo_config,
    print_scenario_catalog,
    probe_relivio_runtime,
    register_deployment,
    resolve_scenario_name,
    scenario_details,
    summarize_trigger_results,
    trigger_failures,
)
from demo_scenarios import scenario_choices
from mcp_lib import get_verdict_via_mcp, list_recent_deployments_via_mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full Relivio demo using the Python SDK for supply and relivio-mcp for verdict consumption."
    )
    parser.add_argument(
        "--scenario",
        choices=scenario_choices(),
        default="risk-demo",
        help="Which failure pattern to trigger after deploy registration.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print the available demo scenarios and exit.",
    )
    parser.add_argument("--count", type=int, help="Override how many failing requests to trigger.")
    parser.add_argument("--version", help="Optional deployment version label.")
    parser.add_argument("--note", default="fastapi sdk+mcp demo flow", help="Optional deployment note.")
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=5,
        help="How many recent deployments MCP should inspect when resolving the newest deployment.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=15.0,
        help="Polling interval while waiting for the verdict.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=960.0,
        help="Maximum wait time for the verdict.",
    )
    args = parser.parse_args()

    if args.list_scenarios:
        print_scenario_catalog()
        return

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)
    details = scenario_details(scenario)

    print("Relivio backend demo agent cycle")
    print(
        "scenario: "
        f"{details['name']} | intended_outcome={details['intended_outcome']} | "
        f"default_count={details['default_count']}"
    )
    print(f"scenario_summary: {details['summary']}")

    app_ok, app_message = check_app_health(config)
    print(f"1/6 app health: {'OK' if app_ok else 'FAIL'} - {app_message}")
    if not app_ok:
        raise SystemExit(1)

    runtime_ok, runtime_message = probe_relivio_runtime(config)
    print(f"2/6 runtime probe: {'OK' if runtime_ok else 'FAIL'} - {runtime_message}")
    if not runtime_ok:
        raise SystemExit(1)

    deployment_id, version = register_deployment(
        config,
        version=args.version,
        note=args.note,
    )
    print(f"3/6 deployment registered via SDK: deployment_id={deployment_id} version={version}")

    results = trigger_failures(
        config,
        scenario=scenario,
        count=count,
    )
    distinct_paths = sorted({str(item['path']) for item in results})
    trigger_summary = summarize_trigger_results(results)
    status_summary = ", ".join(
        f"{status}x{count}" for status, count in sorted(trigger_summary["status_counts"].items())
    )
    print(
        "4/6 scenario triggered: "
        f"scenario={scenario} count={len(results)} routes={', '.join(distinct_paths)}"
    )
    print(f"   trigger_statuses: {status_summary}")

    deployments = list_recent_deployments_via_mcp(
        api_url=config.relivio_api_base_url,
        api_key=config.relivio_project_api_key,
        limit=args.recent_limit,
    )
    if not deployments:
        print("5/6 recent deployments via MCP: FAIL - no deployments returned")
        raise SystemExit(1)

    selected_deployment_id = str(deployments[0]["deployment_id"])
    print(
        "5/6 recent deployments via MCP: "
        f"selected_deployment_id={selected_deployment_id} latest_window_status={deployments[0].get('window_status')}"
    )

    result = get_verdict_via_mcp(
        api_url=config.relivio_api_base_url,
        api_key=config.relivio_project_api_key,
        deployment_id=selected_deployment_id,
    )

    import time

    deadline = time.monotonic() + max(args.timeout_seconds, 0.0)
    poll = 0
    while result.get("status") == "pending" and time.monotonic() < deadline:
        poll += 1
        print(
            "6/6 verdict via MCP: "
            f"pending (poll {poll}), retrying in {args.interval_seconds:g}s"
        )
        time.sleep(max(args.interval_seconds, 0.5))
        result = get_verdict_via_mcp(
            api_url=config.relivio_api_base_url,
            api_key=config.relivio_project_api_key,
            deployment_id=selected_deployment_id,
        )

    if result.get("status") == "pending":
        print("6/6 verdict via MCP: TIMEOUT")
        print(
            "Run this to keep polling manually: "
            "python scripts/check_verdict_via_mcp.py --latest-deployment --wait"
        )
        raise SystemExit(1)

    print("6/6 verdict via MCP")
    print_verdict(result)


if __name__ == "__main__":
    main()
