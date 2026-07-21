ICR_STRESS_DELTA   = 0.02   # stress interest rate 2% above current
ICR_MINIMUM        = 1.25   # standard BTL lender minimum ICR
ICR_STRESS_YEARS   = 2      # years of shortfall to capitalise as risk cost
LTV_BUFFER_LOW     = 0.60   # below this: no capital risk cost
LTV_BUFFER_HIGH    = 0.75   # above this: maximum capital risk scaling
LTV_CRASH_SEVERITY = 0.20   # assumed price fall in a downturn stress
LTV_LOW_PENALTY    = 0.05   # max risk cost at LTV_BUFFER_LOW–HIGH band
CONC_THRESHOLD     = 0.60   # single-region share above which penalty applies
CONC_SEVERITY      = 0.10   # max additional loss as fraction of portfolio value
EPC_DISCOUNT       = 0.15   # forced-sale discount for non-compliant properties


BANK_PRICE_SHOCK = 0.20  # hypothetical downturn applied before scoring LTV


def compute_bank_score(risk_breakdown):
    """Convert a risk_breakdown dict into a 0-100 bank risk score and label.

    LTV is stressed by a 20% price shock before scoring — this reflects what a
    bank sees after a downturn, not the appreciated end-state value.
    """
    ltv_current = risk_breakdown.get("portfolio_ltv_pct", 0) / 100
    # Apply price shock: if prices fall 20%, mortgage stays fixed so LTV rises
    ltv       = ltv_current / (1 - BANK_PRICE_SHOCK)
    icr       = risk_breakdown.get("stressed_icr")
    conc      = risk_breakdown.get("max_region_pct", 0) / 100
    epc_pct   = risk_breakdown.get("non_compliant_pct", 0) / 100

    # LTV penalty (0–35)
    if ltv <= 0.60:
        ltv_pen = 0
    elif ltv <= 0.75:
        ltv_pen = round(20 * (ltv - 0.60) / 0.15)
    else:
        ltv_pen = round(20 + 15 * min(1.0, (ltv - 0.75) / 0.25))

    # Stressed ICR penalty (0–35)
    if icr is None:
        icr_pen = 0
    elif icr >= 2.0:
        icr_pen = 0
    elif icr >= 1.25:
        icr_pen = round(15 * (2.0 - icr) / 0.75)
    else:
        icr_pen = round(15 + 20 * min(1.0, (1.25 - icr) / 1.25))

    # Concentration penalty (0–15)
    conc_pen = round(15 * min(1.0, max(0, conc - 0.60) / 0.40)) if conc > 0.60 else 0

    # EPC penalty (0–15)
    epc_pen = round(15 * min(1.0, epc_pct))

    score = max(0, 100 - ltv_pen - icr_pen - conc_pen - epc_pen)

    if score >= 80:
        label = "Investment Grade"
    elif score >= 60:
        label = "Acceptable Risk"
    elif score >= 40:
        label = "Enhanced Monitoring"
    elif score >= 20:
        label = "Watch List"
    else:
        label = "Default Risk"

    return score, label


class ScoringEngine:
    def record_rent(self, actor_id, amount):
        pass   # tracked directly on ActorState.total_rent_received

    def compute_risk_cost(self, actor, properties, macro_rate):
        prop_map = {p.id: p for p in properties}
        held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
        empty = {"icr_cost": 0.0, "ltv_capital_cost": 0.0, "concentration_cost": 0.0,
                 "epc_cost": 0.0, "total": 0.0, "stressed_icr": None,
                 "portfolio_ltv_pct": 0.0, "max_region_pct": 0.0,
                 "top_region": "", "non_compliant_pct": 0.0, "non_compliant_value": 0.0}
        if not held:
            return 0.0, empty

        total_value    = sum(p.current_value for p in held)
        total_mortgage = sum(p.mortgage_balance for p in held)
        annual_rent    = sum(p.rent * 12 for p in held)
        leveraged      = [p for p in held if p.mortgage_balance > 0]

        # 1. ICR stress test: recalculate at current rate + 2%
        stressed_annual_interest = sum(
            p.mortgage_balance * (p.mortgage_rate + ICR_STRESS_DELTA) for p in leveraged
        )
        if stressed_annual_interest > 0:
            stressed_icr = annual_rent / stressed_annual_interest
            if stressed_icr < ICR_MINIMUM:
                annual_shortfall = stressed_annual_interest * ICR_MINIMUM - annual_rent
                icr_cost = annual_shortfall * ICR_STRESS_YEARS
            else:
                icr_cost = 0.0
        else:
            stressed_icr = None
            icr_cost = 0.0

        # 2. LTV capital risk: potential loss in a price correction
        ltv = total_mortgage / total_value if total_value > 0 else 0.0
        if ltv > LTV_BUFFER_HIGH:
            ltv_cost = total_value * LTV_CRASH_SEVERITY * min(1.0, (ltv - LTV_BUFFER_HIGH) / (1.0 - LTV_BUFFER_HIGH))
        elif ltv > LTV_BUFFER_LOW:
            ltv_cost = total_value * LTV_LOW_PENALTY * (ltv - LTV_BUFFER_LOW) / (LTV_BUFFER_HIGH - LTV_BUFFER_LOW)
        else:
            ltv_cost = 0.0

        # 3. Concentration risk: regional downturn exposure
        region_values = {}
        for p in held:
            region_values[p.region] = region_values.get(p.region, 0) + p.current_value
        max_region_pct = max(region_values.values()) / total_value if total_value > 0 else 1.0
        if max_region_pct > CONC_THRESHOLD:
            concentration_cost = total_value * CONC_SEVERITY * (max_region_pct - CONC_THRESHOLD) / (1.0 - CONC_THRESHOLD)
        else:
            concentration_cost = 0.0

        # 4. EPC regulatory risk: forced-sale discount on non-compliant properties
        # Band 4 = D (acceptable); only E (5), F (6), G (7) carry the penalty
        non_compliant       = [p for p in held if p.epc_band >= 5]
        non_compliant_value = sum(p.current_value for p in non_compliant)
        epc_cost            = non_compliant_value * EPC_DISCOUNT

        total_risk_cost = round(icr_cost + ltv_cost + concentration_cost + epc_cost, 0)
        breakdown = {
            "icr_cost":            round(icr_cost, 0),
            "ltv_capital_cost":    round(ltv_cost, 0),
            "concentration_cost":  round(concentration_cost, 0),
            "epc_cost":            round(epc_cost, 0),
            "total":               total_risk_cost,
            "stressed_icr":        round(stressed_icr, 2) if stressed_icr is not None else None,
            "portfolio_ltv_pct":   round(ltv * 100, 1),
            "max_region_pct":      round(max_region_pct * 100, 1),
            "top_region":          max(region_values, key=region_values.get) if region_values else "",
            "non_compliant_pct":   round(non_compliant_value / total_value * 100, 1) if total_value > 0 else 0.0,
            "non_compliant_value": round(non_compliant_value, 0),
        }
        return total_risk_cost, breakdown

    def compute_scores(self, state):
        macro_rate = state.macro.interest_rate
        prop_map   = {p.id: p for p in state.properties}
        scores     = {}
        for actor_id, actor in state.actors.items():
            current_pv     = sum(prop_map[pid].current_value - prop_map[pid].mortgage_balance
                             for pid in actor.portfolio if pid in prop_map)
            capital_return = sum(prop_map[pid].current_value - prop_map[pid].base_value
                                 for pid in actor.portfolio if pid in prop_map)
            income_return  = actor.total_rent_received
            total_return   = current_pv + actor.cash - actor.initial_wealth

            risk_cost, risk_breakdown = self.compute_risk_cost(actor, state.properties, macro_rate)
            final_score = round(total_return - risk_cost, 0)

            gross_pv       = sum(prop_map[pid].current_value
                                 for pid in actor.portfolio if pid in prop_map)
            total_mortgage = sum(prop_map[pid].mortgage_balance
                                 for pid in actor.portfolio if pid in prop_map)
            scores[actor_id] = {
                "actor_id":             actor_id,
                "name":                 actor.name,
                "gross_portfolio_value": round(gross_pv, 0),
                "total_mortgage":       round(total_mortgage, 0),
                "initial_wealth":       round(actor.initial_wealth, 0),
                "portfolio_value":      round(current_pv, 0),
                "cash":                 round(actor.cash, 0),
                "income_return":        round(income_return, 0),
                "capital_return":       round(capital_return, 0),
                "total_return":         round(total_return, 0),
                "risk_cost":            risk_cost,
                "risk_breakdown":       risk_breakdown,
                "final_score":          final_score,
            }
        return scores

    def leaderboard(self, state):
        scores = self.compute_scores(state)
        return sorted(scores.values(), key=lambda s: s["final_score"], reverse=True)
