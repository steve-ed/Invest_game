MORTGAGE_SPREAD  = 0.018   # lender margin above BoE base rate
MGMT_FEE_RATE    = 0.12    # letting agent full management fee
INSURANCE_RATE   = 0.0015  # buildings + landlord liability insurance (% of value per year)


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
                    # Auto-remortgage: fixed term expired last tick and actor didn't refi.
                    # Charge 1% arrangement fee and lock into a new 2-year fix at current rate.
                    if not prop.is_fixed_rate and prop.fixed_ticks_remaining == 0:
                        fee = round(prop.mortgage_balance * 0.01)
                        actor.cash -= fee
                        actor.total_transaction_costs += fee
                        prop.mortgage_rate = state.macro.interest_rate + MORTGAGE_SPREAD
                        prop.is_fixed_rate = True
                        prop.fixed_ticks_remaining = 4

                    rate = prop.mortgage_rate if prop.is_fixed_rate else state.macro.interest_rate + MORTGAGE_SPREAD
                    interest = prop.mortgage_balance * rate / 2
                    actor.cash -= interest
                    actor.total_mortgage_paid += interest
                    if prop.fixed_ticks_remaining > 0:
                        prop.fixed_ticks_remaining -= 1
                        if prop.fixed_ticks_remaining == 0:
                            prop.is_fixed_rate = False
                            prop.mortgage_rate = state.macro.interest_rate + MORTGAGE_SPREAD

            # Insurance (buildings + landlord liability, 0.15% of value per year, semi-annual)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop:
                    premium = prop.current_value * INSURANCE_RATE / 2
                    actor.cash -= premium
                    actor.total_insurance_paid += premium

            # Rent collection (monthly rent × 6 months per semi-annual tick)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop is None:
                    continue
                if prop.epc_void:
                    pass  # permanently void until upgraded to EPC C or better
                elif prop.void_ticks_remaining > 0:
                    prop.void_ticks_remaining -= 1
                else:
                    gross = prop.rent * 6
                    income = gross * (1 - MGMT_FEE_RATE)
                    actor.cash += income
                    actor.total_rent_received += income

            # Income tax on rental profit (player only, based on tax_mode)
            tax_mode = getattr(actor, 'tax_mode', 'none')
            if tax_mode != 'none':
                for pid in actor.portfolio:
                    prop = prop_map.get(pid)
                    if prop is None or prop.epc_void or prop.void_ticks_remaining > 0:
                        continue
                    net_6m      = prop.rent * 6 * (1 - MGMT_FEE_RATE)
                    interest_6m = prop.mortgage_balance * prop.mortgage_rate / 2 if prop.mortgage_balance > 0 else 0.0
                    if tax_mode == 'basic':
                        # Full mortgage interest relief at basic rate
                        tax = max(0.0, (net_6m - interest_6m) * 0.20)
                    elif tax_mode == 'higher':
                        # Section 24: tax gross income at 40%, credit back 20% of interest
                        tax = max(0.0, net_6m * 0.40 - interest_6m * 0.20)
                    elif tax_mode == 'company':
                        # Full interest deductibility at corporation tax rate
                        tax = max(0.0, (net_6m - interest_6m) * 0.25)
                    else:
                        tax = 0.0
                    if tax > 0:
                        actor.cash -= tax
                        actor.total_tax_paid += tax

            events.append({
                "type": "actor_step",
                "tick": tick,
                "actor_id": actor_id,
                "cash": actor.cash,
                "detail": f"Actor {actor.name}: cash={actor.cash:.2f}",
            })

        return events
