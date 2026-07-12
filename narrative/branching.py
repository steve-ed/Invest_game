HIGH_RATE_THRESHOLD = 0.07

_STRESS_TEXTS = [
    "High interest rates are squeezing landlord margins across the market.",
    "Mortgage costs rise sharply, putting pressure on leveraged investors.",
]

_STABLE_TEXTS = [
    "Market conditions remain within normal parameters.",
    "Investor sentiment holds steady as rates stay manageable.",
]


class BranchingEngine:
    def step(self, state, tick):
        if state.macro.interest_rate > HIGH_RATE_THRESHOLD:
            branch = "stress"
            detail = _STRESS_TEXTS[tick % len(_STRESS_TEXTS)]
        else:
            branch = "stable"
            detail = _STABLE_TEXTS[tick % len(_STABLE_TEXTS)]
        return [{
            "type": "narrative_branch",
            "tick": tick,
            "branch": branch,
            "detail": detail,
        }]
