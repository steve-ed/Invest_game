from void_maintenance import expected_maintenance_reserve

YIELD_TARGET          = 0.06    # minimum gross annual yield to buy (yield strategy)
YIELD_MAX_RATE        = 0.07    # yield AI holds when BoE rate exceeds this
LEVERAGE_MAX_RATE_BUY = 0.065   # leverage AI only buys when rate <= this
LEVERAGE_SELL_RATE    = 0.085   # leverage AI sells when rate exceeds this
LTV_LEVERAGE          = 0.75
LTV_MODERATE          = 0.50
LTV_VALUE_ADD         = 0.65    # bridging-style LTV for value_add buyers
LTV_LOW               = 0.35    # conservative leverage for yield strategy
CAPITAL_MIN_VALUE     = 150_000  # capital strategy targets higher-value properties
VALUE_ADD_MIN_VALUE   = 120_000  # value_add avoids lowest-growth cheap stock
CAPITAL_MAX_RATE      = 0.065   # capital growth pauses buying above this rate
CAPITAL_FALL_TICKS    = 2       # consecutive falling price ticks before selling
BRRR_RECYCLE_SIZE     = 4       # sell when portfolio reaches this size
BRRR_RATE_GATE        = 0.07    # BRRR pauses buying above this rate
BRRR_SELL_RATE        = 0.10    # BRRR force-sells at critical rates
_BRRR_UPGRADE_COST    = {4: 5_000, 5: 8_000, 6: 10_000, 7: 10_000}
DEMO_MAX_RATE         = 0.065   # demographic pauses buying above this rate
DEMO_SELL_RENT_TICKS  = 3       # consecutive negative rent growth ticks before selling


class AIController:
    def step(self, state, tick):
        owned_all = {pid for a in state.actors.values() for pid in a.portfolio}
        available = [p for p in state.properties if p.id not in owned_all]
        events = []
        for actor_id, actor in state.actors.items():
            if actor_id == "player":
                continue
            action, property_id, ltv = self._decide(state, actor, available)
            events.append({
                "type": "ai_action",
                "tick": tick,
                "actor_id": actor_id,
                "action": action,
                "property_id": property_id,
                "ltv": ltv,
                "detail": f"AI {actor.name} [{actor.strategy}]: {action}"
                          + (f" {property_id}" if property_id else ""),
            })
            if action == "buy" and property_id:
                available = [p for p in available if p.id != property_id]
        return events

    def _decide(self, state, actor, available):
        strategy = actor.strategy
        if strategy == "yield":
            return self._decide_yield(state, actor, available)
        if strategy == "leverage":
            return self._decide_leverage(state, actor, available)
        if strategy == "capital":
            return self._decide_capital(state, actor, available)
        if strategy == "value_add":
            return self._decide_value_add(state, actor, available)
        if strategy == "brrr":
            return self._decide_brrr(state, actor, available)
        if strategy == "demographic":
            return self._decide_demographic(state, actor, available)
        if strategy == "balanced":
            return self._decide_balanced(state, actor, available)
        return "hold", None, 0.0

    def _check_upgrade(self, state, actor):
        """Return upgrade action for the worst-EPC owned property if affordable, else None."""
        prop_map = {p.id: p for p in state.properties}
        candidates = sorted(
            [(pid, prop_map[pid]) for pid in actor.portfolio if pid in prop_map and prop_map[pid].epc_band >= 4],
            key=lambda x: -x[1].epc_band,
        )
        for pid, prop in candidates:
            cost = _BRRR_UPGRADE_COST.get(prop.epc_band, 0)
            if cost > 0 and actor.cash >= cost * 1.5:
                return "upgrade", pid, 0.0
        return None

    def _decide_yield(self, state, actor, available):
        upg = self._check_upgrade(state, actor)
        if upg: return upg
        rate = state.macro.interest_rate
        if rate > YIELD_MAX_RATE:
            return "hold", None, 0.0
        for prop in sorted(available, key=lambda p: -(p.rent * 12) / p.current_value):
            gross_yield = (prop.rent * 12) / prop.current_value
            if gross_yield < YIELD_TARGET:
                continue
            # Use low LTV to scale portfolio while keeping ICR healthy
            deposit = prop.current_value * (1 - LTV_LOW)
            if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop):
                return "buy", prop.id, LTV_LOW
        return "hold", None, 0.0

    def _decide_leverage(self, state, actor, available):
        upg = self._check_upgrade(state, actor)
        if upg: return upg
        rate = state.macro.interest_rate
        if rate > LEVERAGE_SELL_RATE and actor.portfolio:
            return "sell", self._highest_ltv_hold(actor, state), 0.0
        if rate <= LEVERAGE_MAX_RATE_BUY:
            for prop in available:
                deposit = prop.current_value * (1 - LTV_LEVERAGE)
                if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop):
                    return "buy", prop.id, LTV_LEVERAGE
        return "hold", None, 0.0

    def _decide_capital(self, state, actor, available):
        upg = self._check_upgrade(state, actor)
        if upg: return upg
        rate = state.macro.interest_rate
        history = state.macro_history

        # Sell only after sustained price falls, and sell the weakest performer
        if len(history) >= CAPITAL_FALL_TICKS + 1:
            falling = all(
                history[-(i+1)].price_index < history[-(i+2)].price_index
                for i in range(CAPITAL_FALL_TICKS)
            )
            if falling and actor.portfolio:
                return "sell", self._worst_capital_hold(actor, state), 0.0

        # Rate gate: capital gains evaporate when mortgage costs are high
        if rate > CAPITAL_MAX_RATE:
            return "hold", None, 0.0

        candidates = sorted(
            [p for p in available if p.current_value >= CAPITAL_MIN_VALUE],
            key=lambda p: -p.current_value,
        )
        for prop in candidates:
            deposit = prop.current_value * (1 - LTV_MODERATE)
            if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop):
                return "buy", prop.id, LTV_MODERATE
        return "hold", None, 0.0

    def _decide_value_add(self, state, actor, available):
        prop_map = {p.id: p for p in state.properties}

        # Upgrade owned distressed properties before buying new ones
        for pid in actor.portfolio:
            prop = prop_map.get(pid)
            if prop and prop.epc_band >= 4:
                cost = _BRRR_UPGRADE_COST.get(prop.epc_band, 0)
                if cost > 0 and actor.cash >= cost * 1.5:
                    return "upgrade", pid, 0.0

        # Refi compliant properties to recycle uplift from completed upgrades
        for pid in sorted(
            actor.portfolio,
            key=lambda pid: prop_map[pid].current_value * LTV_VALUE_ADD - prop_map[pid].mortgage_balance
                            if pid in prop_map else 0,
            reverse=True,
        ):
            prop = prop_map.get(pid)
            if prop and prop.epc_band < 4 and prop.fixed_ticks_remaining == 0:
                headroom = prop.current_value * LTV_VALUE_ADD - prop.mortgage_balance
                if headroom >= 20_000:
                    return "refi", pid, LTV_VALUE_ADD

        candidates = sorted(
            [p for p in available
             if (p.epc_band >= 4 or p.archetype == "value_add")
             and p.current_value >= VALUE_ADD_MIN_VALUE],
            key=lambda p: -(p.rent * 12) / p.current_value,
        )
        for prop in candidates:
            upgrade_reserve = _BRRR_UPGRADE_COST.get(prop.epc_band, 0) if prop.epc_band >= 4 else 0
            deposit = prop.current_value * (1 - LTV_VALUE_ADD)
            if actor.cash >= deposit * 1.05 + upgrade_reserve + expected_maintenance_reserve(prop):
                return "buy", prop.id, LTV_VALUE_ADD
        return "hold", None, 0.0

    def _decide_brrr(self, state, actor, available):
        rate = state.macro.interest_rate
        prop_map = {p.id: p for p in state.properties}

        # Sell only when rate is high AND portfolio is cash-flow negative under stress
        if rate > BRRR_SELL_RATE and actor.portfolio:
            held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
            annual_rent = sum(p.rent * 12 for p in held)
            stressed_interest = sum(
                p.mortgage_balance * (p.mortgage_rate + 0.02) for p in held if p.mortgage_balance > 0
            )
            if stressed_interest > 0 and annual_rent < stressed_interest:
                return "sell", self._brrr_worst_hold(actor, prop_map), 0.0

        # Refurbish owned distressed properties before acquiring new ones
        for pid in actor.portfolio:
            prop = prop_map.get(pid)
            if prop and prop.epc_band >= 4:
                cost = _BRRR_UPGRADE_COST.get(prop.epc_band, 0)
                if cost > 0 and actor.cash >= cost * 1.5:
                    return "upgrade", pid, 0.0

        # Recycle equity: refi any compliant property with headroom at 75% LTV
        refi_candidates = sorted(
            [pid for pid in actor.portfolio
             if prop_map.get(pid) and prop_map[pid].fixed_ticks_remaining == 0
             and prop_map[pid].epc_band < 4
             and prop_map[pid].current_value * LTV_LEVERAGE > prop_map[pid].mortgage_balance + 10_000],
            key=lambda pid: prop_map[pid].current_value * LTV_LEVERAGE - prop_map[pid].mortgage_balance,
            reverse=True,
        )
        if refi_candidates:
            # Only refi early (before portfolio is full) if there's a buy candidate to deploy into
            if len(actor.portfolio) >= BRRR_RECYCLE_SIZE or rate <= BRRR_RATE_GATE and any(
                actor.cash + (prop_map[refi_candidates[0]].current_value * LTV_LEVERAGE
                              - prop_map[refi_candidates[0]].mortgage_balance)
                >= p.current_value * (1 - LTV_LEVERAGE) * 1.1 + expected_maintenance_reserve(p)
                   + (_BRRR_UPGRADE_COST.get(p.epc_band, 0) if p.epc_band >= 4 else 0)
                for p in available
            ):
                return "refi", refi_candidates[0], LTV_LEVERAGE

        # Sell only when portfolio is full and no refi is available
        if len(actor.portfolio) >= BRRR_RECYCLE_SIZE:
            return "sell", self._brrr_worst_hold(actor, prop_map), 0.0

        # Rate gate: avoid buying into high-rate environments
        if rate > BRRR_RATE_GATE:
            return "hold", None, 0.0

        # Buy: target distressed stock AND high-yield archetypes (HMO, short_let),
        # ranked by projected post-upgrade yield so best cash-flow comes first
        def _post_upgrade_yield(p):
            upgrade_cost = _BRRR_UPGRADE_COST.get(p.epc_band, 0) if p.epc_band >= 4 else 0
            projected_rent = p.rent * (1.10 if upgrade_cost > 0 else 1.0)
            return (projected_rent * 12) / (p.current_value + upgrade_cost) if p.current_value > 0 else 0

        candidates = sorted(
            [p for p in available
             if p.epc_band >= 4 or p.archetype in ("value_add", "hmo", "short_let")],
            key=_post_upgrade_yield,
            reverse=True,
        )
        if not candidates:
            candidates = sorted(available, key=_post_upgrade_yield, reverse=True)
        for prop in candidates:
            deposit = prop.current_value * (1 - LTV_LEVERAGE)
            upgrade_reserve = _BRRR_UPGRADE_COST.get(prop.epc_band, 0) if prop.epc_band >= 4 else 0
            if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop) + upgrade_reserve:
                return "buy", prop.id, LTV_LEVERAGE
        return "hold", None, 0.0

    def _decide_demographic(self, state, actor, available):
        upg = self._check_upgrade(state, actor)
        if upg: return upg
        rate = state.macro.interest_rate
        history = state.macro_history
        prop_map = {p.id: p for p in state.properties}

        # Sell when rent growth has been negative for sustained period
        if len(history) >= DEMO_SELL_RENT_TICKS and actor.portfolio:
            neg_rent = all(
                history[-(i+1)].rent_growth < 0
                for i in range(DEMO_SELL_RENT_TICKS)
            )
            if neg_rent:
                return "sell", actor.portfolio[0], 0.0

        # Don't buy at high rates or when rent growth has been flat/falling for 2 ticks
        avg_rent_growth = (
            sum(h.rent_growth for h in history[-2:]) / 2
            if len(history) >= 2 else state.macro.rent_growth
        )
        if rate > DEMO_MAX_RATE or avg_rent_growth <= 0:
            return "hold", None, 0.0

        held_regions = {prop_map[pid].region for pid in actor.portfolio if pid in prop_map}
        candidates = sorted(
            available,
            key=lambda p: (p.region in held_regions, -p.rent / p.current_value),
        )
        for prop in candidates:
            deposit = prop.current_value * (1 - LTV_MODERATE)
            if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop):
                return "buy", prop.id, LTV_MODERATE
        return "hold", None, 0.0

    def _decide_balanced(self, state, actor, available):
        upg = self._check_upgrade(state, actor)
        if upg: return upg
        rate = state.macro.interest_rate
        if rate > 0.06:
            return "hold", None, 0.0
        for prop in available:
            gross_yield = (prop.rent * 12) / prop.current_value
            if gross_yield >= 0.04:
                deposit = prop.current_value * (1 - LTV_MODERATE)
                if actor.cash >= deposit * 1.1 + expected_maintenance_reserve(prop):
                    return "buy", prop.id, LTV_MODERATE
        return "hold", None, 0.0

    def _brrr_worst_hold(self, actor, prop_map):
        """Least capital-appreciated property in portfolio."""
        held = [(pid, prop_map[pid]) for pid in actor.portfolio if pid in prop_map]
        if not held:
            return actor.portfolio[0]
        held.sort(key=lambda x: (x[1].current_value - x[1].base_value) / max(x[1].base_value, 1))
        return held[0][0]

    def _worst_capital_hold(self, actor, state):
        """Lowest capital gain property — sell this first."""
        prop_map = {p.id: p for p in state.properties}
        held = [(pid, prop_map[pid]) for pid in actor.portfolio if pid in prop_map]
        if not held:
            return actor.portfolio[0]
        held.sort(key=lambda x: x[1].current_value - x[1].base_value)
        return held[0][0]

    def _highest_ltv_hold(self, actor, state):
        """Highest LTV property — most exposed when rates are high."""
        prop_map = {p.id: p for p in state.properties}
        held = [(pid, prop_map[pid]) for pid in actor.portfolio if pid in prop_map]
        if not held:
            return actor.portfolio[0]
        held.sort(key=lambda x: x[1].mortgage_balance / max(x[1].current_value, 1), reverse=True)
        return held[0][0]
