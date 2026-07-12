"""
Headless verification run: 3 games, full transaction log + analytics table audit.

Focus: verify the 'total' column in actors_data vs the correct net-worth calculation.

Run: python verify_transactions.py
"""

import collections
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

READY_PATH      = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH     = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")
TURN_STATE_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "turn_state.json")

# ── Minimal player engine ────────────────────────────────────────────────────

class HoldPlayer:
    """Always holds — simplest possible player so we can track AI transactions."""
    def step(self, state, tick):
        with open(ACTION_PATH, "w", encoding="utf-8") as f:
            json.dump({"action": "hold", "property_id": None, "ltv": 0.0}, f)
        return [{
            "type": "player_action", "tick": tick, "actor_id": "player",
            "action": "hold", "property_id": None, "ltv": 0.0,
            "detail": "verify: hold",
        }]


# ── Patch kernel I/O ─────────────────────────────────────────────────────────

def _patch_kernel(kernel_module):
    _orig_exists = os.path.exists
    _orig_remove = os.remove
    _ready_norm  = os.path.normcase(READY_PATH)

    def _patched_exists(path):
        return True if os.path.normcase(path) == _ready_norm else _orig_exists(path)

    def _patched_remove(path):
        if os.path.normcase(path) != _ready_norm:
            _orig_remove(path)

    kernel_module.os.path.exists = _patched_exists
    kernel_module.os.remove      = _patched_remove


# ── Run one game, capture everything ────────────────────────────────────────

SEP = "─" * 90

def run_game(game_num, SimulationKernel):
    kernel = SimulationKernel(turns=20, mode="student", turn_delay=0)
    kernel.player_choices = HoldPlayer()

    transactions = []   # all buy/sell/refi/upgrade events
    tick_snapshots = [] # per-tick actor state

    original_write = kernel._write_turn_state

    def intercepting_write(tick_events_arg, *args, is_final=False):
        tick = kernel.state.tick
        prop_map = {p.id: p for p in kernel.state.properties}

        # Capture transactions from this tick
        for ev in tick_events_arg:
            if ev.get("type") not in ("player_action", "ai_action"):
                continue
            action = ev.get("action", "hold")
            if action == "hold":
                continue
            pid = ev.get("property_id") or ""
            actor_id = ev.get("actor_id", "?")
            actor = kernel.state.actors.get(actor_id)
            prop  = prop_map.get(pid)
            transactions.append({
                "game":     game_num,
                "tick":     tick,
                "actor":    actor_id,
                "action":   action,
                "prop":     pid,
                "value":    round(prop.current_value, 0) if prop else None,
                "mortgage": round(prop.mortgage_balance, 0) if prop else None,
                "cash_after": round(actor.cash, 0) if actor else None,
            })

        # Write first, then read back the actual total the kernel produced
        original_write(tick_events_arg, *args, is_final=is_final)

        try:
            with open(TURN_STATE_PATH, encoding="utf-8") as _f:
                _written = json.load(_f)
            written_totals = {aid: d["total"] for aid, d in _written.get("actors", {}).items()}
        except Exception:
            written_totals = {}

        snap = {"game": game_num, "tick": tick, "actors": {}}
        for actor_id, actor in kernel.state.actors.items():
            held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
            gross_pv = sum(p.current_value for p in held)
            total_mortgage = sum(p.mortgage_balance for p in held)
            equity = gross_pv - total_mortgage
            correct_total = round(actor.cash + equity, 2)
            actual_total  = written_totals.get(actor_id, correct_total)

            snap["actors"][actor_id] = {
                "cash":              round(actor.cash, 0),
                "gross_pv":         round(gross_pv, 0),
                "total_mortgage":   round(total_mortgage, 0),
                "equity":           round(equity, 0),
                "actors_data_total": actual_total,
                "wealth_total":     correct_total,
                "mismatch":         abs(actual_total - correct_total) > 1,
            }
        tick_snapshots.append(snap)

    kernel._write_turn_state = intercepting_write
    results = kernel.run()

    return results, transactions, tick_snapshots


# ── Report ───────────────────────────────────────────────────────────────────

def report(game_num, results, transactions, snapshots):
    print(f"\n{'='*90}")
    print(f"GAME {game_num}  |  era: {results.get('era_label', '?')}")
    print(f"{'='*90}")

    # Transactions
    print(f"\n{'TRANSACTIONS':}")
    print(f"  {'Tick':>4}  {'Actor':<10}  {'Action':<8}  {'Prop':<6}  {'Value':>10}  {'Mortgage':>10}  {'CashAfter':>12}")
    print(f"  {SEP}")
    for t in transactions:
        print(f"  {t['tick']:>4}  {t['actor']:<10}  {t['action']:<8}  {t['prop']:<6}  "
              f"{t['value'] or 0:>10,.0f}  {t['mortgage'] or 0:>10,.0f}  "
              f"{t['cash_after'] or 0:>12,.0f}")

    # Analytics table audit: show every tick where actors_data total != wealth total
    mismatches = [
        (s["tick"], aid, d)
        for s in snapshots
        for aid, d in s["actors"].items()
        if d["mismatch"]
    ]

    print(f"\n{'ANALYTICS TABLE — TOTAL COLUMN AUDIT':}")
    print(f"  Checking: actors_data['total'] = cash + gross_pv")
    print(f"  Correct:  wealth_history total  = cash + equity (= gross_pv - mortgage)")
    print()

    # Show final tick in detail
    final_snap = snapshots[-1]
    print(f"  FINAL TICK ({final_snap['tick']}) breakdown:")
    print(f"  {'Actor':<10}  {'Cash':>10}  {'GrossPV':>10}  {'Mortgage':>10}  {'Equity':>10}  "
          f"{'actors_data_total':>18}  {'wealth_total':>12}  {'Match?':>7}")
    print(f"  {SEP}")
    for aid, d in final_snap["actors"].items():
        match = "OK" if not d["mismatch"] else "MISMATCH"
        print(f"  {aid:<10}  {d['cash']:>10,.0f}  {d['gross_pv']:>10,.0f}  "
              f"{d['total_mortgage']:>10,.0f}  {d['equity']:>10,.0f}  "
              f"{d['actors_data_total']:>18,.0f}  {d['wealth_total']:>12,.0f}  {match:>7}")

    if mismatches:
        print(f"\n  Ticks with mismatch: {len(mismatches)}")
        first_10 = mismatches[:10]
        for tick, aid, d in first_10:
            diff = d['actors_data_total'] - d['wealth_total']
            print(f"    tick={tick:>2}  {aid:<10}  diff=£{diff:>+12,.0f}  "
                  f"(mortgage=£{d['total_mortgage']:,.0f})")
    else:
        print(f"\n  No mismatches found — actors_data_total matches wealth_total (no mortgages?)")

    # Leaderboard
    print(f"\n{'LEADERBOARD':}")
    lb = results.get("leaderboard", [])
    for rank, e in enumerate(lb, 1):
        print(f"  {rank}. {e['name']:<22}  score=£{e['final_score']:>12,.0f}"
              f"  equity=£{e['portfolio_value']:>10,.0f}  cash=£{e['cash']:>10,.0f}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)

    import kernel as kernel_module
    from kernel import SimulationKernel

    _patch_kernel(kernel_module)

    all_mismatches = 0

    for g in range(1, 4):
        results, transactions, snapshots = run_game(g, SimulationKernel)
        report(g, results, transactions, snapshots)

        for s in snapshots:
            for aid, d in s["actors"].items():
                if d["mismatch"]:
                    all_mismatches += 1

    print(f"\n{'='*90}")
    print(f"SUMMARY: Total mismatch-ticks across 3 games: {all_mismatches}")
    if all_mismatches > 0:
        print("  CONCLUSION: actors_data['total'] = cash + gross_pv (INCLUDES mortgage debt)")
        print("  FIX NEEDED: should be cash + equity (= cash + gross_pv - mortgage_balance)")
    else:
        print("  actors_data['total'] matches wealth_history in all ticks.")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
