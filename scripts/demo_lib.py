from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pprint import pprint

import httpx
from dotenv import load_dotenv

from demo_scenarios import (
    default_failure_count_for_scenario,
    describe_scenarios,
    get_scenario_definition,
    planned_paths_for_scenario,
    resolve_scenario_name,
)


@dataclass(frozen=True)
class DemoConfig:
    relivio_api_base_url: str
    relivio_project_api_key: str
    relivio_service_name: str
    app_base_url: str


def build_relivio_client(config: DemoConfig):
    from relivio import Relivio

    return Relivio(
        api_key=config.relivio_project_api_key,
        base_url=config.relivio_api_base_url,
    )


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
        relivio_service_name=(os.getenv("RELIVIO_SERVICE_NAME") or "relivio-demo-fastapi").strip()
        or "relivio-demo-fastapi",
        app_base_url=(os.getenv("APP_BASE_URL") or "http://127.0.0.1:8000").strip().rstrip("/"),
    )

def build_deploy_version(prefix: str = "relivio-demo") -> str:
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
    from relivio import RelivioApiError

    try:
        build_relivio_client(config).verdicts.latest()
    except RelivioApiError as exc:
        if exc.status == 401:
            return False, "Relivio runtime probe returned 401. Check RELIVIO_PROJECT_API_KEY."
        return False, f"Relivio runtime probe failed with status {exc.status}: {exc}"
    except Exception as exc:
        return False, f"Relivio runtime probe failed: {exc}"
    return True, "Relivio runtime probe reached the project-scoped verdict surface"


def register_deployment(
    config: DemoConfig,
    *,
    version: str | None = None,
    note: str = "fastapi example deploy",
) -> tuple[str, str]:
    from relivio import RegisterDeploymentInput

    resolved_version = version or build_deploy_version()
    response = build_relivio_client(config).deployments.register(
        RegisterDeploymentInput(
            version=resolved_version,
            note=note,
            metadata={
                "source": "relivio-demo-fastapi",
                "environment": "demo",
                "demo_flow": "true",
            },
            idempotency_key=f"deploy:{resolved_version}",
        )
    )
    return response.id, resolved_version


def trigger_failures(
    config: DemoConfig,
    *,
    scenario: str,
    count: int,
    path: str = "/demo/fail",
) -> list[dict[str, object]]:
    resolved_scenario = resolve_scenario_name(scenario)
    planned_paths = (path,) if resolved_scenario == "single-demo" else planned_paths_for_scenario(resolved_scenario)
    results: list[dict[str, object]] = []
    with httpx.Client(timeout=3.0) as client:
        for index in range(count):
            resolved_path = planned_paths[index % len(planned_paths)]
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


def summarize_trigger_results(results: list[dict[str, object]]) -> dict[str, object]:
    status_counts: dict[int, int] = {}
    path_counts: dict[str, int] = {}
    for item in results:
        status_code = int(item["status_code"])
        path = str(item["path"])
        status_counts[status_code] = status_counts.get(status_code, 0) + 1
        path_counts[path] = path_counts.get(path, 0) + 1
    return {
        "total": len(results),
        "status_counts": status_counts,
        "path_counts": path_counts,
    }


def print_scenario_catalog() -> None:
    print("Available demo scenarios")
    for item in describe_scenarios():
        print(
            f"- {item['name']} ({', '.join(str(name) for name in item['all_names'])})"
        )
        print(f"  intended_outcome={item['intended_outcome']}")
        print(f"  default_count={item['default_count']}")
        print(f"  manual_route={item['manual_route']}")
        print(f"  summary={item['summary']}")


def scenario_details(raw: str) -> dict[str, object]:
    scenario = get_scenario_definition(raw)
    return scenario.to_dict()


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


def fetch_recent_deployments(
    config: DemoConfig,
    *,
    limit: int = 5,
) -> httpx.Response:
    return httpx.get(
        f"{config.relivio_api_base_url}/api/v1/deployments/recent",
        headers={"X-API-Key": config.relivio_project_api_key},
        params={"limit": max(1, min(int(limit), 20))},
        timeout=5.0,
    )


def list_recent_deployments(
    config: DemoConfig,
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    response = fetch_recent_deployments(config, limit=limit)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"recent deployments payload missing items: {payload}")
    return [item for item in items if isinstance(item, dict)]


def resolve_latest_deployment_id(
    config: DemoConfig,
    *,
    limit: int = 5,
) -> str | None:
    items = list_recent_deployments(config, limit=limit)
    if not items:
        return None
    deployment_id = items[0].get("deployment_id")
    if not deployment_id:
        return None
    return str(deployment_id)


def print_recent_deployments(items: list[dict[str, object]]) -> None:
    if not items:
        print("No recent deployments found.")
        return

    for index, item in enumerate(items, start=1):
        deployment_id = item.get("deployment_id")
        version = item.get("version")
        deployed_at = item.get("deployed_at")
        window_status = item.get("window_status")
        print(
            f"{index}. deployment_id={deployment_id} "
            f"version={version} deployed_at={deployed_at} window_status={window_status}"
        )


def wait_for_summary(
    config: DemoConfig,
    *,
    deployment_id: str | None,
    interval_seconds: float,
    timeout_seconds: float,
    on_retry: Callable[[int, float], None] | None = None,
) -> dict[str, object] | None:
    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    attempt = 0

    while True:
        response = fetch_summary(config, deployment_id=deployment_id)
        if response.status_code != 404:
            response.raise_for_status()
            return response.json()

        if time.monotonic() >= deadline:
            return None

        attempt += 1
        if on_retry is not None:
            on_retry(attempt, interval_seconds)
        time.sleep(max(interval_seconds, 0.5))


def print_summary(payload: dict[str, object]) -> None:
    print(f"verdict={payload.get('verdict')}")
    print(f"decision_tier={payload.get('decision_tier')}")
    print(f"score={payload.get('score')}")
    print(f"recommended_action={payload.get('recommended_action')}")
    print(f"recommended_action_detail={payload.get('recommended_action_detail')}")
    print(f"affected_apis={payload.get('affected_apis')}")
    content = payload.get("content")
    if isinstance(content, str) and content.strip():
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        if first_line:
            print(f"content_preview={first_line}")

    guidance = payload.get("protection_guidance")
    if guidance:
        print("protection_guidance:")
        pprint(guidance)
