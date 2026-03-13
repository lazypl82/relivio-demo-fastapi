from __future__ import annotations

import argparse

from demo_lib import (
    check_app_health,
    default_failure_count_for_scenario,
    load_demo_config,
    print_summary,
    probe_relivio_runtime,
    register_deployment,
    resolve_scenario_name,
    trigger_failures,
    wait_for_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Relivio backend demo flow.")
    parser.add_argument(
        "--scenario",
        choices=("single", "single-demo", "risk", "risk-demo"),
        default="risk-demo",
        help="Which failure pattern to trigger after deploy registration.",
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

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)

    print("Relivio backend demo flow")

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
    print(
        "4/5 failures triggered: "
        f"scenario={scenario} count={len(results)} routes={', '.join(distinct_paths)}"
    )

    summary = wait_for_summary(
        config,
        deployment_id=deployment_id,
        interval_seconds=args.interval_seconds,
        timeout_seconds=args.timeout_seconds,
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
