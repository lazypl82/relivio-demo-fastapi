from __future__ import annotations

import argparse

from demo_lib import load_demo_config, register_deployment


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a deployment with Relivio.")
    parser.add_argument("--version", help="Deployment version label.")
    parser.add_argument("--note", default="fastapi example deploy", help="Optional deployment note.")
    args = parser.parse_args()

    config = load_demo_config()
    deployment_id, version = register_deployment(
        config,
        version=args.version,
        note=args.note,
    )

    print(f"deployment_id={deployment_id}")
    print(f"version={version}")
    print("summary_note=In the hosted environment, the summary is usually ready after the observation window closes.")
    print("next:")
    print("  1) Trigger an error: curl http://127.0.0.1:8000/demo/fail")
    print(
        f"  2) Wait for the verdict: python scripts/check_summary.py --deployment-id {deployment_id} --wait"
    )


if __name__ == "__main__":
    main()
