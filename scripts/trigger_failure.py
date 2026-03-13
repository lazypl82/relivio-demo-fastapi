from __future__ import annotations

import argparse

from demo_lib import (
    default_failure_count_for_scenario,
    load_demo_config,
    resolve_scenario_name,
    trigger_failures,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger one or more failing requests.")
    parser.add_argument("--path", default="/demo/fail", help="Path to call on the local example app.")
    parser.add_argument("--count", type=int, help="How many times to call the failing endpoint.")
    parser.add_argument(
        "--scenario",
        choices=("single", "single-demo", "risk", "risk-demo"),
        default="single-demo",
        help="Use one path repeatedly or cycle through a stronger risk demo mix.",
    )
    args = parser.parse_args()

    config = load_demo_config()
    scenario = resolve_scenario_name(args.scenario)
    count = args.count if args.count is not None else default_failure_count_for_scenario(scenario)
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


if __name__ == "__main__":
    main()
