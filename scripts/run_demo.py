from __future__ import annotations

import argparse

from demo_lib import (
    check_app_health,
    default_failure_count_for_scenario,
    load_demo_config,
    print_scenario_catalog,
    probe_relivio_runtime,
    register_deployment,
    resolve_scenario_name,
    scenario_choices,
    scenario_details,
    summarize_trigger_results,
    trigger_failures,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register one demo deployment and emit shaped FastAPI signals through the Relivio SDK."
    )
    parser.add_argument(
        "--scenario",
        choices=scenario_choices(),
        default="watch-demo",
        help="Which signal pattern to trigger after deploy registration.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print the available demo scenarios and exit.",
    )
    parser.add_argument("--count", type=int, help="Override how many local requests to trigger.")
    parser.add_argument("--version", help="Optional deployment version label.")
    parser.add_argument("--note", default="fastapi sdk demo flow", help="Optional deployment note.")
    args = parser.parse_args()

    if args.list_scenarios:
        print_scenario_catalog()
        return

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)
    details = scenario_details(scenario)

    print("Relivio FastAPI SDK demo")
    print(
        "scenario: "
        f"{details['name']} | intended_outcome={details['intended_outcome']} | "
        f"default_count={details['default_count']}"
    )
    print(f"scenario_summary: {details['summary']}")

    app_ok, app_message = check_app_health(config)
    print(f"1/4 app health: {'OK' if app_ok else 'FAIL'} - {app_message}")
    if not app_ok:
        raise SystemExit(1)

    runtime_ok, runtime_message = probe_relivio_runtime(config)
    print(f"2/4 Relivio API probe: {'OK' if runtime_ok else 'FAIL'} - {runtime_message}")
    if not runtime_ok:
        raise SystemExit(1)

    deployment_id, version = register_deployment(
        config,
        version=args.version,
        note=args.note,
    )
    print(f"3/4 deployment registered via SDK: deployment_id={deployment_id} version={version}")

    results = trigger_failures(
        config,
        scenario=scenario,
        count=count,
    )
    distinct_signals = sorted({str(item["signal"]) for item in results})
    trigger_summary = summarize_trigger_results(results)
    status_summary = ", ".join(
        f"{status}x{total}" for status, total in sorted(trigger_summary["status_counts"].items())
    )
    print(
        "4/4 scenario emitted through local FastAPI app: "
        f"scenario={scenario} count={len(results)} signals={', '.join(distinct_signals)}"
    )
    print(f"   trigger_statuses: {status_summary}")
    print()
    print("Next:")
    print("- Wait for the observation window to close.")
    print("- Ask your MCP-enabled agent to inspect this deployment through Relivio.")
    print("- Start with the first affected API from the verdict before broad debugging.")
    print("- Leave feedback/correction if the verdict was wrong, useful, or led to rollback.")
    print(f"- deployment_id={deployment_id}")
    print("- If you need a raw HTTP fallback: python scripts/check_summary.py --deployment-id " f"{deployment_id} --wait")


if __name__ == "__main__":
    main()
