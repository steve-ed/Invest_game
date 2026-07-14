"""
Headless game driver: Claude plays the player role.

Usage:
    python claude_player.py
    python claude_player.py --turns 20 --games 10 --log results.txt

Replaces the file-based PlayerChoiceEngine with a rule-based decision
function, bypasses the dashboard handshake, and runs N full games with
turn_delay=0. All actor actions (player + AI) are logged every tick for
post-game analysis and action-coverage verification.
"""

import argparse
import collections
import io
import json
import os
import sys
import time

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

READY_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")

# ── Decision constants ──────────────────────────────────────────────────────

BUY_LTV             = 0.75
BUY_CASH_RESERVE    = 150_000
SELL_HIGH_LTV       = 0.80
HIGH_RATE_THRESHOLD = 0.065
EPC_UPGRADE_RESERVE = 2.0
EPC_COST            = {4: 5_000, 5: 8_000, 6: 10_000, 7: 10_000}


# ── Claude player engine ────────────────────────────────────────────────────

class ClaudePlayerEngine:
    """
    Balanced property investor:
    - Refinances when fixed term expires and equity headroom >= £20k.
    - Upgrades worst EPC property when affordable.
    - Sells mortgaged property when rates spike and LTV > 80%.
    - Buys when rates <= 6.5%, yield > 5.5%, and cash covers deposit + reserve.
    - Otherwise holds.
    """

    def step(self, state, tick):
        action, property_id, ltv, rationale = self._decide(state)
        _log(f"    PLAYER  {action:<8} {property_id or '':>4}  ltv={ltv:.0%}"
             f"  [{rationale}]")
        with open(ACTION_PATH, "w", encoding="utf-8") as f:
            json.dump({"action": action, "property_id": property_id, "ltv": ltv}, f)
        return [{
            "type":        "player_action",
            "tick":        tick,
            "actor_id":    "player",
            "action":      action,
            "property_id": property_id,
            "ltv":         ltv,
            "detail":      f"Claude: {action}{' ' + property_id if property_id else ''}",
        }]

    def _decide(self, state):
        actor = state.actors.get("player")
        if not actor:
            return "hold", None, 0.0, "no player actor"

        prop_map  = {p.id: p for p in state.properties}
        held      = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
        owned_all = {pid for a in state.actors.values() for pid in a.portfolio}
        available = [p for p in state.properties if p.id not in owned_all]
        rate      = state.macro.interest_rate

        # 1. Refinance: extract equity on expired fixed terms
        for prop in held:
            if prop.fixed_ticks_remaining == 0 and prop.mortgage_balance > 0:
                headroom = max(0.0, prop.current_value * 0.75 - prop.mortgage_balance)
                if headroom >= 20_000:
                    return "refi", prop.id, 0.75, f"headroom=£{headroom:,.0f}"

        # 2. Upgrade worst EPC property
        for pid, prop in sorted(
            [(pid, prop_map[pid]) for pid in actor.portfolio
             if pid in prop_map and prop_map[pid].epc_band >= 4],
            key=lambda x: -x[1].epc_band,
        ):
            cost = EPC_COST.get(prop.epc_band, 0)
            if cost and actor.cash >= cost * EPC_UPGRADE_RESERVE:
                return "upgrade", pid, 0.0, f"EPC={chr(64+prop.epc_band)} cost={cost:,}"

        # 3. Sell if rate spike + high LTV
        if rate > HIGH_RATE_THRESHOLD:
            for prop in sorted(held,
                key=lambda p: -(p.mortgage_balance / p.current_value if p.current_value else 0)):
                ltv_now = prop.mortgage_balance / prop.current_value if prop.current_value else 0
                if ltv_now > SELL_HIGH_LTV:
                    return "sell", prop.id, 0.0, \
                        f"rate={rate:.1%} ltv={ltv_now:.0%}"

        # 4. Buy: low rate + good yield
        if rate <= HIGH_RATE_THRESHOLD:
            for prop in sorted(available,
                               key=lambda p: -(p.rent * 12) / p.current_value):
                gross_yield = (prop.rent * 12) / prop.current_value
                if gross_yield < 0.055:
                    continue
                deposit = prop.current_value * (1 - BUY_LTV)
                total   = deposit + _sdlt(prop.current_value)
                if actor.cash >= total + BUY_CASH_RESERVE:
                    return "buy", prop.id, BUY_LTV, \
                        f"yield={gross_yield:.1%} rate={rate:.1%}"

        return "hold", None, 0.0, f"rate={rate:.1%}"


# ── SDLT helper ──────────────────────────────────────────────────────────────

def _sdlt(price):
    bands = [(125_000, 0.0), (250_000, 0.02), (925_000, 0.05),
             (1_500_000, 0.10), (float("inf"), 0.12)]
    tax, prev = 0.0, 0.0
    for threshold, rate in bands:
        if price <= prev:
            break
        tax  += (min(price, threshold) - prev) * rate
        prev  = threshold
    return tax


# ── Logging ──────────────────────────────────────────────────────────────────

_log_file = None

def _log(msg):
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()


# ── Single game runner ───────────────────────────────────────────────────────

def run_game(game_num, turns, kernel_module, SimulationKernel):
    """Run one game, log all actor actions, return leaderboard + action tally."""

    kernel = SimulationKernel(turns=turns, mode="student", turn_delay=0)
    kernel.player_choices = ClaudePlayerEngine()

    player     = kernel.state.actors["player"]
    prop_map   = {p.id: p for p in kernel.state.properties}
    actor_names = {aid: a.name for aid, a in kernel.state.actors.items()}
    actor_names["player"] = "You (Claude)"

    _log(f"\n{'='*70}")
    _log(f"GAME {game_num}  |  {turns} turns  |  era: {kernel.era_label}")
    _log(f"{'='*70}")
    _log(f"  Starting cash: £{player.cash:,.0f}")
    for pid in player.portfolio:
        p = prop_map[pid]
        _log(f"  {pid}  {p.region:<20} £{p.current_value:>9,.0f}  "
             f"yield={p.rent*12/p.current_value:.1%}  EPC={chr(64+p.epc_band)}")

    # Track actions seen this game
    action_tally = collections.Counter()   # (actor_id, action) -> count
    executed     = []                       # list of {tick, actor, action, prop, ok}

    # Wrap _write_turn_state to log tick summary + all actor actions
    original_write = kernel._write_turn_state

    def logged_write(tick_events_arg, *args, is_final=False):
        tick  = kernel.state.tick
        actor = kernel.state.actors.get("player")
        if actor and tick > 0:
            pm     = {p.id: p for p in kernel.state.properties}
            held   = [pm[pid] for pid in actor.portfolio if pid in pm]
            equity = sum(p.current_value - p.mortgage_balance for p in held)
            rate   = kernel.state.macro.interest_rate
            pi     = kernel.state.macro.price_index
            _log(f"\n  -- Tick {tick:>2}  PI={pi:.1f}  Rate={rate:.1%}"
                 f"  Scenario={kernel.state.current_scenario}")
            _log(f"     Player: cash=£{actor.cash:>10,.0f}  "
                 f"equity=£{equity:>10,.0f}  "
                 f"net=£{actor.cash+equity:>10,.0f}  "
                 f"props={actor.portfolio}")

            # Log all actor actions from this tick's events
            for ev in tick_events_arg:
                if ev.get("type") not in ("player_action", "ai_action"):
                    continue
                aid    = ev.get("actor_id", "?")
                action = ev.get("action", "hold")
                pid    = ev.get("property_id") or ""
                ltv    = ev.get("ltv", 0.0)
                name   = actor_names.get(aid, aid)

                # Verify whether action actually took effect.
                # For upgrade/refi: property may have been force-sold by the EPC
                # mandate in the same tick — that's not an action failure.
                act_obj      = kernel.state.actors.get(aid)
                portfolio_now = act_obj.portfolio if act_obj else []
                force_sold   = {
                    ev2.get("property_id")
                    for ev2 in tick_events_arg
                    if ev2.get("type") == "epc_force_sell"
                }

                if action == "buy":
                    ok     = pid in portfolio_now
                    status = "OK" if ok else "FAILED"
                elif action == "sell":
                    ok     = pid not in portfolio_now
                    status = "OK" if ok else "FAILED"
                elif action == "upgrade":
                    if pid in portfolio_now:
                        ok, status = True, "OK"
                    elif pid in force_sold:
                        ok, status = True, "OK (force-sold after upgrade)"
                    else:
                        ok, status = False, "FAILED"
                elif action == "refi":
                    if pid in portfolio_now:
                        ok, status = True, "OK"
                    elif pid in force_sold:
                        ok, status = True, "OK (force-sold after refi)"
                    else:
                        ok, status = False, "FAILED"
                else:
                    ok, status = True, "OK"
                if ev.get("type") == "ai_action":
                    _log(f"     AI    [{name:<20}]  {action:<8} {pid:>4}  "
                         f"ltv={ltv:.0%}  [{status}]")

                action_tally[(aid, action)] += 1
                executed.append({
                    "game": game_num, "tick": tick, "actor": aid,
                    "action": action, "property": pid, "ok": ok,
                })

        original_write(tick_events_arg, *args, is_final=is_final)

    kernel._write_turn_state = logged_write

    results = kernel.run()

    _log(f"\n  LEADERBOARD (game {game_num}):")
    lb = results["leaderboard"]
    player_rank = None
    for rank, entry in enumerate(lb, 1):
        marker = " <--" if entry["actor_id"] == "player" else ""
        _log(f"    {rank}. {entry['name']:<22}"
             f"  score=£{entry['final_score']:>12,.0f}"
             f"  equity=£{entry['portfolio_value']:>10,.0f}"
             f"  cash=£{entry['cash']:>10,.0f}{marker}")
        if entry["actor_id"] == "player":
            player_rank = rank

    return lb, action_tally, executed, player_rank, kernel.era_label


# ── Kernel patches (applied once, persist across all games) ─────────────────

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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global _log_file

    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=20)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--log",   type=str, default=None)
    args = parser.parse_args()

    if args.log:
        _log_file = open(args.log, "w", encoding="utf-8")

    os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)

    import kernel as kernel_module
    from kernel import SimulationKernel

    _patch_kernel(kernel_module)

    # Aggregate across all games
    all_executed     = []
    all_action_tally = collections.Counter()
    game_summaries   = []

    for g in range(1, args.games + 1):
        lb, tally, executed, rank, era = run_game(
            g, args.turns, kernel_module, SimulationKernel)
        all_executed     += executed
        all_action_tally += tally
        player_entry = next((e for e in lb if e["actor_id"] == "player"), {})
        game_summaries.append({
            "game":      g,
            "era":       era,
            "rank":      rank,
            "score":     player_entry.get("final_score", 0),
            "equity":    player_entry.get("portfolio_value", 0),
            "cash":      player_entry.get("cash", 0),
        })

    # ── Cross-game summary ────────────────────────────────────────────────────
    _log(f"\n\n{'='*70}")
    _log(f"SUMMARY — {args.games} games x {args.turns} turns")
    _log(f"{'='*70}")

    _log("\nPer-game results (Claude / player):")
    _log(f"  {'Game':<6} {'Era':<40} {'Rank':<6} {'Score':>14}")
    wins = 0
    for s in game_summaries:
        if s["rank"] == 1:
            wins += 1
        _log(f"  {s['game']:<6} {s['era']:<40} {s['rank']:<6} £{s['score']:>12,.0f}")
    avg_score = sum(s["score"] for s in game_summaries) / len(game_summaries)
    avg_rank  = sum(s["rank"]  for s in game_summaries) / len(game_summaries)
    _log(f"\n  Avg score: £{avg_score:,.0f}   Avg rank: {avg_rank:.1f}/3   Wins: {wins}/{args.games}")

    _log("\nAction coverage — all actors across all games:")
    action_types = ["buy", "sell", "upgrade", "refi", "hold"]
    actors_seen  = sorted({aid for aid, _ in all_action_tally})
    header = f"  {'Actor':<24}" + "".join(f"{a:>10}" for a in action_types)
    _log(header)
    for aid in actors_seen:
        row = f"  {aid:<24}" + "".join(
            f"{all_action_tally[(aid, a)]:>10}" for a in action_types)
        _log(row)

    _log("\nAction success/failure breakdown:")
    from collections import defaultdict
    results_map = defaultdict(lambda: {"ok": 0, "fail": 0})
    for ev in all_executed:
        key = (ev["actor"], ev["action"])
        if ev["ok"]:
            results_map[key]["ok"] += 1
        else:
            results_map[key]["fail"] += 1
    _log(f"  {'Actor+Action':<30} {'OK':>8} {'FAILED':>8}")
    for (aid, action) in sorted(results_map):
        r = results_map[(aid, action)]
        _log(f"  {aid+'/'+action:<30} {r['ok']:>8} {r['fail']:>8}")

    if _log_file:
        _log_file.close()
        print(f"\nLog written to: {args.log}")


if __name__ == "__main__":
    main()
