from __future__ import annotations

import argparse

from demo_lib import (
    default_failure_count_for_scenario,
    load_demo_config,
    print_scenario_catalog,
    resolve_scenario_name,
    scenario_details,
    summarize_trigger_results,
    trigger_failures,
)
from demo_scenarios import scenario_choices


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger one or more failing requests.")
    parser.add_argument("--path", default="/demo/fail", help="Path to call on the local example app.")
    parser.add_argument("--count", type=int, help="How many times to call the failing endpoint.")
    parser.add_argument(
        "--scenario",
        choices=scenario_choices(),
        default="single-demo",
        help="Run a minimal stable/watch/risk-shaped demo sequence.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print the available demo scenarios and exit.",
    )
    args = parser.parse_args()

    if args.list_scenarios:
        print_scenario_catalog()
        return

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)
    details = scenario_details(scenario)
    print(
        "scenario: "
        f"{details['name']} | intended_outcome={details['intended_outcome']} | "
        f"default_count={details['default_count']}"
    )
    print(f"scenario_summary: {details['summary']}")
    results = trigger_failures(
        config,
        scenario=scenario,
        count=count,
        path=args.path,
    )
    for result in results:
        print(
            f"{result['index']}: path={result['path']} "
            f"status={result['status_code']} body={result['body']}"
        )
    summary = summarize_trigger_results(results)
    status_summary = ", ".join(
        f"{status}x{count}" for status, count in sorted(summary["status_counts"].items())
    )
    print(f"summary: total={summary['total']} statuses={status_summary}")


if __name__ == "__main__":
    main()
