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


def run_doctor() -> None:
    config = load_demo_config()
    print("Relivio demo doctor")
    print(f"- app_base_url={config.app_base_url}")
    print(f"- relivio_api_base_url={config.relivio_api_base_url}")
    print(f"- service_name={config.relivio_service_name}")

    app_ok, app_message = check_app_health(config)
    print(f"- app_health={'OK' if app_ok else 'FAIL'}: {app_message}")

    runtime_ok, runtime_message = probe_relivio_runtime(config)
    print(f"- runtime_probe={'OK' if runtime_ok else 'FAIL'}: {runtime_message}")

    if app_ok and runtime_ok:
        print("doctor_status=ready")
        return

    print("doctor_status=not_ready")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register one demo deployment and emit shaped FastAPI signals through the Relivio SDK."
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check local app and Relivio API readiness without registering a deployment.",
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
    parser.add_argument("--version", help="Optional deployment version label.")
    parser.add_argument("--note", default="fastapi sdk demo flow", help="Optional deployment note.")
    args = parser.parse_args()

    if args.doctor:
        run_doctor()
        return

    if args.list_scenarios:
        print_scenario_catalog()
        return

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = default_failure_count_for_scenario(scenario)
    details = scenario_details(scenario)

    print("Relivio FastAPI SDK demo")
    print(
        "scenario: "
        f"{details['name']} | intended_outcome={details['intended_outcome']} | "
        f"default_count={details['default_count']}"
    )
    print(f"scenario_summary: {details['summary']}")
    print(
        "signal_schedule: "
        f"realistic | duration_seconds={details['estimated_realistic_duration_seconds']}"
    )

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
    if results:
        last_offset = results[-1].get("scheduled_offset_seconds")
        print(f"   last_scheduled_signal_at_seconds={last_offset}")
    print()
    print("Next:")
    print("- Check the active-window provisional read before the final window closes:")
    print("  python scripts/check_summary.py --provisional --deployment-id " f"{deployment_id} --wait")
    print("- Wait for the observation window to close for the final verdict.")
    print("- Ask your MCP-enabled agent to inspect this deployment through Relivio.")
    print("- Start with the first affected API from the verdict before broad debugging.")
    print("- Leave feedback/correction if the verdict was wrong, useful, or led to rollback.")
    print(f"- deployment_id={deployment_id}")
    print("- If you need a raw HTTP fallback: python scripts/check_summary.py --deployment-id " f"{deployment_id} --wait")


if __name__ == "__main__":
    main()
