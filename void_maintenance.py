"""
Void period and maintenance/capex event engine.

Called once per tick BEFORE actors.step() so that void events suppress
the current tick's rent collection (actors.py already checks
prop.void_ticks_remaining > 0 and skips rent for those properties).

Probability model
-----------------
Void:
  Base rate by archetype (per 6-month tick):
    btl        8%   (~1.6 voids per 20-tick game on average)
    hmo        3%   (multiple rooms buffer against full void)
    new_build  4%   (lets quickly, warranty appeal)
    short_let 12%   (high tenant turnover)
    value_add 10%   (distressed stock harder to let)
  EPC D +2%, E +4%, F +6%, G +8%   (poor energy ratings deter tenants)
  Falling rent market +5%

Maintenance:
  Probability by age band (per 6-month tick):
    <15 yrs  3%   new — warranty covers most defects
    15-50    8%   modern — occasional system failures
    50-70   13%   period — aging fabric and services
    70+     20%   old — frequent and potentially serious
  HMO archetype +5%   (higher tenant density accelerates wear)
  Costs scaled by age band; drawn from weighted distribution.
"""

import random

# ── Void parameters ──────────────────────────────────────────────────────────

_VOID_BASE = {
    "btl":       0.08,
    "hmo":       0.03,
    "new_build": 0.04,
    "short_let": 0.12,
    "value_add": 0.10,
}
_VOID_EPC_EXTRA = {4: 0.02, 5: 0.04, 6: 0.06, 7: 0.08}
_VOID_NEG_RENT  = 0.05   # extra when rent_growth <= 0

# ── Maintenance parameters ───────────────────────────────────────────────────

# (max_age, probability, [(cost, weight), ...])
_MAINT_PROFILE = [
    (15,  0.03, [(300, 0.60), (800,   0.40)]),
    (50,  0.08, [(500, 0.45), (2000,  0.40), (5000,  0.15)]),
    (70,  0.13, [(1000,0.35), (3000,  0.45), (8000,  0.20)]),
    (999, 0.20, [(1500,0.25), (5000,  0.45), (12000, 0.30)]),
]
_MAINT_HMO_EXTRA = 0.05

_MAINT_LABEL = {
    300:   "minor repair",
    500:   "minor repair",
    800:   "minor repair",
    1000:  "plumbing fault",
    1500:  "plumbing fault",
    2000:  "electrical or plumbing fault",
    3000:  "heating system repair",
    5000:  "boiler replacement",
    8000:  "structural repair",
    12000: "roof or structural work",
}

# Maintenance reserve an actor should hold per property (used by ai.py)
_MAINT_RESERVE = [
    (15,  2_000),
    (50,  5_000),
    (70,  10_000),
    (999, 15_000),
]


def expected_maintenance_reserve(prop):
    """Minimum cash reserve an actor should hold for one maintenance event."""
    for max_age, reserve in _MAINT_RESERVE:
        if prop.age < max_age:
            return reserve
    return 15_000


def void_risk_pct(prop, macro_history, epc_mandate_announced=False):
    """Expected void probability for display on market property cards."""
    p = _VOID_BASE.get(prop.archetype, 0.08)
    p += _VOID_EPC_EXTRA.get(prop.epc_band, 0)
    if macro_history:
        rg = macro_history[-1].rent_growth if macro_history else 0
        if rg <= 0:
            p += _VOID_NEG_RENT
    return round(p * 100, 0)


def maintenance_risk_label(prop):
    """Low / Medium / High label for display on market property cards."""
    for max_age, prob, _ in _MAINT_PROFILE:
        if prop.age < max_age:
            bonus = _MAINT_HMO_EXTRA if prop.archetype == "hmo" else 0
            total = prob + bonus
            if total < 0.07:
                return "Low"
            if total < 0.15:
                return "Medium"
            return "High"
    return "High"


def _age_profile(age):
    for max_age, prob, costs in _MAINT_PROFILE:
        if age < max_age:
            return prob, costs
    return _MAINT_PROFILE[-1][1], _MAINT_PROFILE[-1][2]


class VoidMaintenanceEngine:
    def step(self, state, tick):
        prop_map = {p.id: p for p in state.properties}
        events   = []

        for actor_id, actor in state.actors.items():
            for pid in list(actor.portfolio):
                prop = prop_map.get(pid)
                if prop is None:
                    continue

                # Skip post-purchase void ticks (already set at acquisition)
                if prop.void_ticks_remaining > 0:
                    continue

                # ── Void event ────────────────────────────────────────────
                void_p = _VOID_BASE.get(prop.archetype, 0.08)
                void_p += _VOID_EPC_EXTRA.get(prop.epc_band, 0)
                if state.macro.rent_growth <= 0:
                    void_p += _VOID_NEG_RENT

                if random.random() < void_p:
                    prop.void_ticks_remaining = 1
                    lost_rent = round(prop.rent * 6, 0)
                    actor.total_void_losses += lost_rent
                    events.append({
                        "type":        "void_period",
                        "tick":        tick,
                        "property_id": pid,
                        "actor_id":    actor_id,
                        "lost_rent":   lost_rent,
                        "detail":      f"{pid} void this period — £{lost_rent:,.0f} rent lost ({actor.name})",
                    })

                # ── Maintenance event ─────────────────────────────────────
                maint_p, cost_dist = _age_profile(prop.age)
                if prop.archetype == "hmo":
                    maint_p += _MAINT_HMO_EXTRA

                if random.random() < maint_p:
                    cost_values = [c for c, _ in cost_dist]
                    cost_weights = [w for _, w in cost_dist]
                    cost  = random.choices(cost_values, weights=cost_weights)[0]
                    label = _MAINT_LABEL.get(cost, "maintenance work")
                    actor.cash -= cost
                    actor.total_maintenance_costs += cost
                    events.append({
                        "type":        "maintenance",
                        "tick":        tick,
                        "property_id": pid,
                        "actor_id":    actor_id,
                        "cost":        cost,
                        "label":       label,
                        "detail":      f"{pid} {label} — £{cost:,} ({actor.name})",
                    })

        return events
