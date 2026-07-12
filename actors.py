MORTGAGE_SPREAD = 0.018  # lender margin above BoE base rate


class ActorManager:
    def step(self, state, tick):
        prop_map = {p.id: p for p in state.properties}
        events = []

        for actor_id, actor in state.actors.items():
            # Savings interest on cash: BoE rate * 0.75 (competitive savings account), semi-annual
            savings_rate = state.macro.interest_rate * 0.75 / 2
            actor.cash *= (1 + savings_rate)

            # Mortgage payments (semi-annual interest)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop and prop.mortgage_balance > 0:
                    rate = prop.mortgage_rate if prop.is_fixed_rate else state.macro.interest_rate + MORTGAGE_SPREAD
                    interest = prop.mortgage_balance * rate / 2
                    actor.cash -= interest
                    actor.total_mortgage_paid += interest
                    if prop.fixed_ticks_remaining > 0:
                        prop.fixed_ticks_remaining -= 1
                        if prop.fixed_ticks_remaining == 0:
                            prop.is_fixed_rate = False
                            prop.mortgage_rate = state.macro.interest_rate + MORTGAGE_SPREAD

            # Rent collection (monthly rent × 6 months per semi-annual tick)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop is None:
                    continue
                if prop.void_ticks_remaining > 0:
                    prop.void_ticks_remaining -= 1
                else:
                    income = prop.rent * 6
                    actor.cash += income
                    actor.total_rent_received += income

            events.append({
                "type": "actor_step",
                "tick": tick,
                "actor_id": actor_id,
                "cash": actor.cash,
                "detail": f"Actor {actor.name}: cash={actor.cash:.2f}",
            })

        return events
