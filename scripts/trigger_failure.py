from __future__ import annotations

import argparse
import os

import httpx
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger one or more failing requests.")
    parser.add_argument("--path", default="/demo/fail", help="Path to call on the local example app.")
    parser.add_argument("--count", type=int, default=3, help="How many times to call the failing endpoint.")
    args = parser.parse_args()

    load_dotenv()

    app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    with httpx.Client(timeout=3.0) as client:
        for index in range(args.count):
            response = client.get(f"{app_base_url}{args.path}")
            print(f"{index + 1}: status={response.status_code} body={response.text}")


if __name__ == "__main__":
    main()
