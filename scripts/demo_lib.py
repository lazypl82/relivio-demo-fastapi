from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pprint import pprint

import httpx
from dotenv import load_dotenv


@dataclass(frozen=True)
class DemoConfig:
    relivio_api_base_url: str
    relivio_project_api_key: str
    relivio_service_name: str
    app_base_url: str


def load_demo_config() -> DemoConfig:
    load_dotenv()

    missing: list[str] = []
    api_base_url = (os.getenv("RELIVIO_API_BASE_URL") or "").strip()
    if not api_base_url:
        missing.append("RELIVIO_API_BASE_URL")

    api_key = (os.getenv("RELIVIO_PROJECT_API_KEY") or "").strip()
    if not api_key:
        missing.append("RELIVIO_PROJECT_API_KEY")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment values: {joined}")

    return DemoConfig(
        relivio_api_base_url=api_base_url.rstrip("/"),
        relivio_project_api_key=api_key,
        relivio_service_name=(os.getenv("RELIVIO_SERVICE_NAME") or "example-fastapi").strip()
        or "example-fastapi",
        app_base_url=(os.getenv("APP_BASE_URL") or "http://127.0.0.1:8000").strip().rstrip("/"),
    )


def resolve_scenario_name(raw: str) -> str:
    normalized = raw.strip().lower()
    aliases = {
        "single": "single-demo",
        "single-demo": "single-demo",
        "risk": "risk-demo",
        "risk-demo": "risk-demo",
    }
    if normalized not in aliases:
        raise RuntimeError(f"Unsupported scenario: {raw}")
    return aliases[normalized]


def default_failure_count_for_scenario(scenario: str) -> int:
    if scenario == "single-demo":
        return 1
    return 8


def build_deploy_version(prefix: str = "example") -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def check_app_health(config: DemoConfig) -> tuple[bool, str]:
    try:
        response = httpx.get(f"{config.app_base_url}/health", timeout=3.0)
    except httpx.HTTPError as exc:
        return False, f"app health request failed: {exc}"
    if response.status_code != 200:
        return False, f"app health returned {response.status_code}: {response.text}"
    return True, "local demo app responded to /health"


def probe_relivio_runtime(config: DemoConfig) -> tuple[bool, str]:
    try:
        response = httpx.get(
            f"{config.relivio_api_base_url}/api/v1/summaries/latest",
            headers={"X-API-Key": config.relivio_project_api_key},
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        return False, f"Relivio runtime probe failed: {exc}"

    if response.status_code in {200, 404}:
        return True, f"Relivio runtime probe returned {response.status_code}"
    if response.status_code == 401:
        return False, "Relivio runtime probe returned 401. Check RELIVIO_PROJECT_API_KEY."
    return False, f"Relivio runtime probe returned {response.status_code}: {response.text}"


def register_deployment(
    config: DemoConfig,
    *,
    version: str | None = None,
    note: str = "fastapi example deploy",
) -> tuple[str, str]:
    resolved_version = version or build_deploy_version()
    response = httpx.post(
        f"{config.relivio_api_base_url}/api/v1/deployments",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": config.relivio_project_api_key,
            "Idempotency-Key": f"deploy:{resolved_version}",
        },
        json={
            "version": resolved_version,
            "note": note,
            "metadata": {
                "source": "relivio-demo-fastapi",
                "environment": "demo",
            },
        },
        timeout=5.0,
    )
    response.raise_for_status()
    payload = response.json()
    deployment_id = payload.get("id") or payload.get("deployment_id")
    if not deployment_id:
        raise RuntimeError(f"deployment id missing in response: {payload}")
    return str(deployment_id), resolved_version


def trigger_failures(
    config: DemoConfig,
    *,
    scenario: str,
    count: int,
    path: str = "/demo/fail",
) -> list[dict[str, object]]:
    resolved_scenario = resolve_scenario_name(scenario)
    risk_paths = (
        "/demo/fail",
        "/demo/fail-timeout",
        "/demo/fail-validation",
        "/demo/fail",
    )
    results: list[dict[str, object]] = []
    with httpx.Client(timeout=3.0) as client:
        for index in range(count):
            resolved_path = path
            if resolved_scenario == "risk-demo":
                resolved_path = risk_paths[index % len(risk_paths)]
            response = client.get(
                f"{config.app_base_url}{resolved_path}",
                headers={"x-request-id": f"demo-{index + 1}-{uuid.uuid4().hex[:12]}"},
            )
            results.append(
                {
                    "index": index + 1,
                    "path": resolved_path,
                    "status_code": response.status_code,
                    "body": response.text,
                }
            )
    return results


def fetch_summary(
    config: DemoConfig,
    *,
    deployment_id: str | None,
) -> httpx.Response:
    params: dict[str, str] = {}
    if deployment_id:
        params["deployment_id"] = deployment_id
    return httpx.get(
        f"{config.relivio_api_base_url}/api/v1/summaries/latest",
        headers={"X-API-Key": config.relivio_project_api_key},
        params=params,
        timeout=5.0,
    )


def wait_for_summary(
    config: DemoConfig,
    *,
    deployment_id: str | None,
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, object] | None:
    deadline = time.monotonic() + max(timeout_seconds, 0.0)

    while True:
        response = fetch_summary(config, deployment_id=deployment_id)
        if response.status_code != 404:
            response.raise_for_status()
            return response.json()

        if time.monotonic() >= deadline:
            return None

        time.sleep(max(interval_seconds, 0.5))


def print_summary(payload: dict[str, object]) -> None:
    print(f"verdict={payload.get('verdict')}")
    print(f"score={payload.get('score')}")
    print(f"recommended_action={payload.get('recommended_action')}")
    print(f"recommended_action_detail={payload.get('recommended_action_detail')}")
    print(f"affected_apis={payload.get('affected_apis')}")

    guidance = payload.get("protection_guidance")
    if guidance:
        print("protection_guidance:")
        pprint(guidance)
