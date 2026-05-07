from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DemoScenario:
    name: str
    aliases: tuple[str, ...]
    default_count: int
    intended_outcome: str
    summary: str
    manual_signal: str
    signal_sequence: tuple[str, ...]

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
        summary="Emits one checkout error so you can verify deploy -> ingest wiring with the smallest signal set.",
        manual_signal="checkout-submit-error",
        signal_sequence=("checkout-submit-error",),
    ),
    "stable-demo": DemoScenario(
        name="stable-demo",
        aliases=("stable",),
        default_count=1,
        intended_outcome="light keep-observing signal",
        summary="Emits one transient profile warning so the output stays small and easy to inspect.",
        manual_signal="profile-warning",
        signal_sequence=("profile-warning",),
    ),
    "watch-demo": DemoScenario(
        name="watch-demo",
        aliases=("watch",),
        default_count=4,
        intended_outcome="guard-ready concentration",
        summary="Concentrates warnings and errors on one orders route so the verdict can look like a contained WATCH-style pattern.",
        manual_signal="order-warning",
        signal_sequence=(
            "order-warning",
            "order-warning",
            "order-error",
            "order-error",
        ),
    ),
    "risk-demo": DemoScenario(
        name="risk-demo",
        aliases=("risk",),
        default_count=15,
        intended_outcome="broader rollback-grade pressure",
        summary="Sustains repeated checkout and payment errors across multiple routes so the signal leans toward rollback-grade pressure.",
        manual_signal="checkout-submit-error",
        signal_sequence=(
            "checkout-submit-error",
            "payment-capture-error",
            "checkout-status-error",
            "checkout-submit-error",
            "payment-capture-error",
            "checkout-status-error",
            "checkout-submit-error",
            "payment-capture-error",
            "checkout-status-error",
            "checkout-submit-error",
            "payment-capture-error",
            "checkout-status-error",
            "checkout-submit-error",
            "payment-capture-error",
            "checkout-status-error",
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


def planned_signals_for_scenario(raw: str) -> tuple[str, ...]:
    return get_scenario_definition(raw).signal_sequence


def describe_scenarios() -> list[dict[str, object]]:
    return [scenario.to_dict() for scenario in SCENARIOS.values()]
