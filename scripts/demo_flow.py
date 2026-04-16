from __future__ import annotations

import argparse

from demo_lib import (
    check_app_health,
    default_failure_count_for_scenario,
    load_demo_config,
    print_scenario_catalog,
    print_summary,
    probe_relivio_runtime,
    register_deployment,
    resolve_scenario_name,
    scenario_details,
    summarize_trigger_results,
    trigger_failures,
    wait_for_summary,
)
from demo_scenarios import scenario_choices


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Relivio backend demo flow.")
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
    parser.add_argument("--note", default="fastapi demo flow", help="Optional deployment note.")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=15.0,
        help="Polling interval while waiting for the summary.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=960.0,
        help="Maximum wait time for the summary.",
    )
    args = parser.parse_args()

    if args.list_scenarios:
        print_scenario_catalog()
        return

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)
    details = scenario_details(scenario)

    print("Relivio backend demo flow")
    print(
        "scenario: "
        f"{details['name']} | intended_outcome={details['intended_outcome']} | "
        f"default_count={details['default_count']}"
    )
    print(f"scenario_summary: {details['summary']}")

    app_ok, app_message = check_app_health(config)
    print(f"1/5 app health: {'OK' if app_ok else 'FAIL'} - {app_message}")
    if not app_ok:
        raise SystemExit(1)

    runtime_ok, runtime_message = probe_relivio_runtime(config)
    print(f"2/5 runtime probe: {'OK' if runtime_ok else 'FAIL'} - {runtime_message}")
    if not runtime_ok:
        raise SystemExit(1)

    deployment_id, version = register_deployment(
        config,
        version=args.version,
        note=args.note,
    )
    print(f"3/5 deployment registered: deployment_id={deployment_id} version={version}")

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
        "4/5 scenario triggered: "
        f"scenario={scenario} count={len(results)} routes={', '.join(distinct_paths)}"
    )
    print(f"   trigger_statuses: {status_summary}")
    print(
        "5/5 summary wait: "
        "observation window is still open; checking for the final verdict until it is ready"
    )

    summary = wait_for_summary(
        config,
        deployment_id=deployment_id,
        interval_seconds=args.interval_seconds,
        timeout_seconds=args.timeout_seconds,
        on_retry=lambda attempt, interval: print(
            "   still waiting: "
            f"summary not ready yet (poll {attempt}, retry in {interval:g}s)"
        ),
    )
    if summary is None:
        print("5/5 summary wait: TIMEOUT")
        print(
            "Run this to keep polling manually: "
            f"python scripts/check_summary.py --deployment-id {deployment_id} --wait"
        )
        raise SystemExit(1)

    print("5/5 summary ready")
    print_summary(summary)


if __name__ == "__main__":
    main()
