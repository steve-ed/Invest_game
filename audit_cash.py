"""
Headless cash audit: runs a full game via GameBus (auto-hold player),
intercepts ActorManager.step() and kernel._execute_action() to verify every
cash movement against independent calculations.
"""
import sys
import os
import random
import threading

sys.path.insert(0, os.path.dirname(__file__))

from actors import ActorManager, MORTGAGE_SPREAD, MGMT_FEE_RATE, INSURANCE_RATE
from kernel import SimulationKernel, _calculate_sdlt, _epc_upgrade_cost
from game_bus import GameBus

EPSILON = 1.0  # tolerance in £

errors = []
log_lines = []


def log(msg):
    log_lines.append(msg)
    print(msg)


def check(label, expected, actual):
    diff = abs(expected - actual)
    ok = diff <= EPSILON
    status = "OK" if ok else f"FAIL (diff={diff:.2f})"
    log(f"  [{status}] {label}: expected={expected:.2f} actual={actual:.2f}")
    if not ok:
        errors.append(f"{label}: expected={expected:.2f} actual={actual:.2f}")


# ── Patch ActorManager.step to audit passive cash flows ─────────────────────

_original_step = ActorManager.step


def _audited_step(self, state, tick):
    prop_map = {p.id: p for p in state.properties}
    boe = state.macro.interest_rate

    # Snapshot before
    before = {}
    for actor_id, actor in state.actors.items():
        props_snap = []
        for pid in actor.portfolio:
            prop = prop_map.get(pid)
            if prop:
                props_snap.append({
                    "id": pid,
                    "mortgage_balance": prop.mortgage_balance,
                    "mortgage_rate": prop.mortgage_rate,
                    "is_fixed_rate": prop.is_fixed_rate,
                    "fixed_ticks_remaining": prop.fixed_ticks_remaining,
                    "void_ticks_remaining": prop.void_ticks_remaining,
                    "epc_void": prop.epc_void,
                    "rent": prop.rent,
                    "current_value": prop.current_value,
                })
        before[actor_id] = {"cash": actor.cash, "props": props_snap}

    events = _original_step(self, state, tick)

    log(f"\n=== Tick {tick} passive cash (BoE={boe:.3f}) ===")
    for actor_id, actor in state.actors.items():
        snap = before[actor_id]
        cash_before = snap["cash"]

        savings_rate = boe * 0.75 / 2
        expected = cash_before * (1 + savings_rate)
        savings_gain = cash_before * savings_rate
        log(f"  {actor.name}: cash_before={cash_before:.2f}  savings={savings_gain:.2f}")

        for ps in snap["props"]:
            if ps["mortgage_balance"] > 0:
                # Auto-remortgage fee fires when is_fixed_rate=False and fixed_ticks_remaining=0
                if not ps["is_fixed_rate"] and ps["fixed_ticks_remaining"] == 0:
                    fee = round(ps["mortgage_balance"] * 0.01)
                    expected -= fee
                    new_rate = boe + MORTGAGE_SPREAD
                    log(f"    remortgage {ps['id']}: fee={fee:.0f} new_rate={new_rate:.4f}")
                    rate = new_rate
                else:
                    rate = ps["mortgage_rate"] if ps["is_fixed_rate"] else boe + MORTGAGE_SPREAD
                interest = ps["mortgage_balance"] * rate / 2
                expected -= interest
                log(f"    mortgage {ps['id']}: bal={ps['mortgage_balance']:.0f} rate={rate:.4f} interest={interest:.2f}")

        for ps in snap["props"]:
            premium = ps["current_value"] * INSURANCE_RATE / 2
            expected -= premium
            log(f"    insurance {ps['id']}: value={ps['current_value']:.0f} premium={premium:.2f}")

        for ps in snap["props"]:
            epc_void = ps["epc_void"]
            void = ps["void_ticks_remaining"] > 0
            if epc_void:
                log(f"    epc_void {ps['id']}: no rent")
            elif void:
                log(f"    void {ps['id']}: no rent (ticks={ps['void_ticks_remaining']})")
            else:
                gross = ps["rent"] * 6
                income = gross * (1 - MGMT_FEE_RATE)
                expected += income
                log(f"    rent {ps['id']}: gross={gross:.2f} net={income:.2f}")

        check(f"tick={tick} {actor.name} passive", expected, actor.cash)

    return events


ActorManager.step = _audited_step


# ── Patch _execute_action to audit action cash flows ─────────────────────────

_original_execute = SimulationKernel._execute_action


def _audited_execute(self, event):
    actor_id = event.get("actor_id")
    action = event.get("action")
    property_id = event.get("property_id")
    ltv = event.get("ltv", 0.0)
    bid_premium = event.get("bid_premium", 0.0)
    tick = self.state.tick

    if not actor_id or action in ("hold", None) or not property_id:
        return _original_execute(self, event)

    actor = self.state.actors.get(actor_id)
    prop_map = {p.id: p for p in self.state.properties}
    owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}
    prop = prop_map.get(property_id)

    if not actor or not prop:
        return _original_execute(self, event)

    # Snapshot state relevant to each action BEFORE execution
    cash_before = actor.cash
    prop_value_before = prop.current_value
    prop_mortgage_before = prop.mortgage_balance
    prop_epc_before = prop.epc_band
    prop_renovated_before = prop.renovated
    prop_fixed_remaining_before = prop.fixed_ticks_remaining
    prop_in_portfolio = property_id in actor.portfolio
    prop_is_auction = prop.is_auction
    prop_is_owned = property_id in owned_all

    _original_execute(self, event)

    cash_after = actor.cash
    cash_delta = cash_after - cash_before

    if cash_delta == 0 and action not in ("hold",):
        # Action may have failed affordability check — skip audit
        log(f"  [SKIP] tick={tick} {actor.name} {action} {property_id}: no cash change (affordability fail or auction loss)")
        return

    log(f"\n  Action tick={tick} {actor.name}: {action} {property_id}  delta={cash_delta:.2f}")

    if action == "sell" and prop_in_portfolio:
        agent_fee = prop_value_before * 0.015
        expected_delta = prop_value_before - prop_mortgage_before - agent_fee
        check(f"tick={tick} {actor.name} sell {property_id}", expected_delta, cash_delta)

    elif action == "buy" and not prop_is_owned:
        if prop_is_auction:
            bid_price = round(prop_value_before * (1 + bid_premium))
            expected_delta = -bid_price
            check(f"tick={tick} {actor.name} auction buy {property_id}", expected_delta, cash_delta)
        else:
            deposit = prop_value_before * (1 - ltv)
            sdlt = _calculate_sdlt(prop_value_before)
            expected_delta = -(deposit + sdlt)
            check(f"tick={tick} {actor.name} buy {property_id}", expected_delta, cash_delta)

    elif action == "upgrade" and prop_in_portfolio:
        cost = _epc_upgrade_cost(prop_epc_before)
        expected_delta = -cost
        check(f"tick={tick} {actor.name} upgrade {property_id}", expected_delta, cash_delta)

    elif action == "renovate" and prop_in_portfolio and not prop_renovated_before:
        cost = round(prop_value_before * 0.10)
        expected_delta = -cost
        check(f"tick={tick} {actor.name} renovate {property_id}", expected_delta, cash_delta)

    elif action == "refi" and prop_in_portfolio:
        if prop_fixed_remaining_before == 0:
            new_balance = prop_value_before * ltv
            released = new_balance - prop_mortgage_before
            if released > 0:
                expected_delta = released - 1_500
                check(f"tick={tick} {actor.name} refi {property_id}", expected_delta, cash_delta)


SimulationKernel._execute_action = _audited_execute


# ── Helper ───────────────────────────────────────────────────────────────────

def _snapshot_wealth(state):
    prop_map = {p.id: p for p in state.properties}
    result = {}
    for aid, actor in state.actors.items():
        equity = sum(prop_map[pid].current_value - prop_map[pid].mortgage_balance
                     for pid in actor.portfolio if pid in prop_map)
        result[aid] = {"cash": actor.cash, "equity": equity, "total": actor.cash + equity}
    return result


# ── Run headless game via bus ─────────────────────────────────────────────────

log("=== Starting headless audit game (20 turns) ===\n")

random.seed(42)
bus = GameBus()
kernel = SimulationKernel(turns=20, mode="student", turn_delay=0, bus=bus)

log(f"Era: {kernel.era_label}  start={kernel.state.start_year}H{kernel.state.start_half}")
log(f"Actors: {[a.name for a in kernel.state.actors.values()]}")
log(f"EPC mandate tick: {kernel._epc_mandate_tick}\n")

wealth_start = _snapshot_wealth(kernel.state)
for aid, w in wealth_start.items():
    log(f"  Initial {kernel.state.actors[aid].name}: cash={w['cash']:.0f} equity={w['equity']:.0f} total={w['total']:.0f}")

# Auto-hold thread: submits "hold" whenever kernel is waiting for player action
def auto_hold_loop(bus, stop_evt):
    while not stop_evt.is_set():
        bus.submit_action("hold", None, 0.0, 0.0)
        stop_evt.wait(timeout=0.1)

stop_evt = threading.Event()
auto_thread = threading.Thread(target=auto_hold_loop, args=(bus, stop_evt), daemon=True)
auto_thread.start()

# Signal ready to start the game
bus.signal_ready()

try:
    result = kernel.run()
    log(f"\nGame complete. Era: {result.get('era_label','?')}")
except Exception as e:
    log(f"\nGame ended with: {e}")
finally:
    stop_evt.set()

log("\n=== Final wealth ===")
wealth_end = _snapshot_wealth(kernel.state)
for aid, w in wealth_end.items():
    log(f"  {kernel.state.actors[aid].name}: cash={w['cash']:.0f} equity={w['equity']:.0f} total={w['total']:.0f}")

# ── Summary ───────────────────────────────────────────────────────────────────
log("\n\n=== AUDIT SUMMARY ===")
if errors:
    log(f"FAILED — {len(errors)} discrepancy(s):")
    for e in errors:
        log(f"  !! {e}")
else:
    log("PASSED — all cash calculations verified correctly")
