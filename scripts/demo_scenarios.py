from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DemoScenario:
    name: str
    aliases: tuple[str, ...]
    default_count: int
    intended_outcome: str
    summary: str
    manual_route: str
    route_sequence: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["all_names"] = self.all_names
        return payload

    @property
    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


SCENARIOS: dict[str, DemoScenario] = {
    "single-demo": DemoScenario(
        name="single-demo",
        aliases=("single",),
        default_count=1,
        intended_outcome="minimal wiring check",
        summary="Calls one path once so you can verify deploy -> ingest -> summary wiring with the smallest signal set.",
        manual_route="/demo/fail",
        route_sequence=("/demo/fail",),
    ),
    "stable-demo": DemoScenario(
        name="stable-demo",
        aliases=("stable",),
        default_count=1,
        intended_outcome="light keep-observing signal",
        summary="Sends one transient warning on a single route so the output stays small and easy to inspect.",
        manual_route="/demo/profile/transient-warning",
        route_sequence=("/demo/profile/transient-warning",),
    ),
    "watch-demo": DemoScenario(
        name="watch-demo",
        aliases=("watch",),
        default_count=4,
        intended_outcome="guard-ready concentration",
        summary="Concentrates warnings and errors on one orders route so the verdict can look like a contained WATCH-style pattern.",
        manual_route="/demo/orders/guard-warning",
        route_sequence=(
            "/demo/orders/guard-warning",
            "/demo/orders/guard-warning",
            "/demo/orders/guard-error",
            "/demo/orders/guard-error",
        ),
    ),
    "risk-demo": DemoScenario(
        name="risk-demo",
        aliases=("risk",),
        default_count=8,
        intended_outcome="broader rollback-grade pressure",
        summary="Spreads repeated errors across checkout and payments routes so the signal looks broader than one noisy endpoint.",
        manual_route="/demo/checkout/submit-error",
        route_sequence=(
            "/demo/checkout/submit-error",
            "/demo/payments/capture-error",
            "/demo/checkout/status-error",
            "/demo/checkout/submit-error",
            "/demo/payments/capture-error",
            "/demo/checkout/status-error",
            "/demo/checkout/submit-error",
            "/demo/payments/capture-error",
        ),
    ),
}


def resolve_scenario_name(raw: str) -> str:
    normalized = raw.strip().lower()
    for scenario in SCENARIOS.values():
        if normalized in scenario.all_names:
            return scenario.name
    raise RuntimeError(f"Unsupported scenario: {raw}")


def scenario_choices() -> tuple[str, ...]:
    choices: list[str] = []
    for scenario in SCENARIOS.values():
        choices.extend(scenario.all_names)
    return tuple(choices)


def default_failure_count_for_scenario(scenario_name: str) -> int:
    return get_scenario_definition(scenario_name).default_count


def get_scenario_definition(raw: str) -> DemoScenario:
    return SCENARIOS[resolve_scenario_name(raw)]


def planned_paths_for_scenario(raw: str) -> tuple[str, ...]:
    return get_scenario_definition(raw).route_sequence


def describe_scenarios() -> list[dict[str, object]]:
    return [scenario.to_dict() for scenario in SCENARIOS.values()]
