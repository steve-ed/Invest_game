_FLAVOUR = {
    "baseline": [
        "Property prices continue their steady upward trend.",
        "Mortgage approvals remain stable this quarter.",
        "New-build completions rise as developer confidence holds.",
    ],
    "downturn": [
        "Mortgage approvals fall to a 10-year low.",
        "Estate agents report a surge in forced sales.",
        "Buy-to-let landlords face mounting pressure as yields compress.",
    ],
    "recovery": [
        "First-time buyer activity picks up as rates begin to ease.",
        "Rental demand rises as market confidence slowly returns.",
        "House price falls slow as buyers return to the market.",
    ],
}


class ScenarioEventEngine:
    def step(self, state, tick):
        texts = _FLAVOUR.get(state.current_scenario, _FLAVOUR["baseline"])
        detail = texts[tick % len(texts)]
        return [{
            "type": "scenario_event",
            "tick": tick,
            "scenario": state.current_scenario,
            "detail": detail,
        }]
