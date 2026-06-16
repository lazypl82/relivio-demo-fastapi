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
    signal_offsets_seconds: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["all_names"] = self.all_names
        payload["estimated_realistic_duration_seconds"] = self.estimated_realistic_duration_seconds
        return payload

    @property
    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)

    @property
    def estimated_realistic_duration_seconds(self) -> int:
        if not self.signal_offsets_seconds:
            return 0
        return int(self.signal_offsets_seconds[-1])


SCENARIOS: dict[str, DemoScenario] = {
    "single-demo": DemoScenario(
        name="single-demo",
        aliases=("single",),
        default_count=1,
        intended_outcome="minimal wiring check",
        summary="Emits one checkout error so you can verify deploy -> ingest wiring with the smallest signal set.",
        manual_signal="checkout-submit-error",
        signal_sequence=("checkout-submit-error",),
        signal_offsets_seconds=(0,),
    ),
    "stable-demo": DemoScenario(
        name="stable-demo",
        aliases=("stable",),
        default_count=1,
        intended_outcome="light keep-observing signal",
        summary="Emits one transient profile warning so the output stays small and easy to inspect.",
        manual_signal="profile-warning",
        signal_sequence=("profile-warning",),
        signal_offsets_seconds=(30,),
    ),
    "watch-demo": DemoScenario(
        name="watch-demo",
        aliases=("watch",),
        default_count=15,
        intended_outcome="rollback-ready WATCH",
        summary="Sustains repeated checkout and payment errors across multiple routes so the current model usually lands in WATCH / rollback-ready.",
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
        signal_offsets_seconds=(
            20,
            55,
            95,
            135,
            180,
            225,
            275,
            325,
            380,
            435,
            500,
            565,
            630,
            700,
            780,
        ),
    ),
    "risk-demo": DemoScenario(
        name="risk-demo",
        aliases=("risk",),
        default_count=18,
        intended_outcome="rollback-grade RISK",
        summary=(
            "Concentrates repeated failures on the payment capture route so the signal "
            "looks route-dominant and rollback-grade instead of broadly noisy."
        ),
        manual_signal="payment-capture-error",
        signal_sequence=(
            "payment-capture-error",
            "payment-capture-error",
            "checkout-submit-error",
            "payment-capture-error",
            "payment-capture-error",
            "payment-capture-error",
            "checkout-status-error",
            "payment-capture-error",
            "payment-capture-error",
            "payment-capture-error",
            "payment-capture-error",
            "payment-capture-error",
            "checkout-submit-error",
            "payment-capture-error",
            "payment-capture-error",
            "checkout-status-error",
            "payment-capture-error",
            "payment-capture-error",
        ),
        signal_offsets_seconds=(
            15,
            40,
            65,
            95,
            130,
            165,
            210,
            255,
            300,
            345,
            390,
            435,
            500,
            565,
            630,
            695,
            760,
            825,
        ),
    ),
    "contained-demo": DemoScenario(
        name="contained-demo",
        aliases=("contained", "guard-demo", "guard"),
        default_count=4,
        intended_outcome="contained route pressure",
        summary="Concentrates warnings and errors on one orders route so you can inspect a smaller guard-style signal.",
        manual_signal="order-warning",
        signal_sequence=(
            "order-warning",
            "order-warning",
            "order-error",
            "order-error",
        ),
        signal_offsets_seconds=(20, 80, 150, 240),
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


def planned_offsets_for_scenario(raw: str) -> tuple[int, ...]:
    return get_scenario_definition(raw).signal_offsets_seconds


def describe_scenarios() -> list[dict[str, object]]:
    return [scenario.to_dict() for scenario in SCENARIOS.values()]
