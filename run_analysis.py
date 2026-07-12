"""
Extended 33-game analysis:
- Logs all actor transactions with year label
- Independently verifies final score vs leaderboard each game
- Compares player vs leverage-strategy bought properties
"""

import argparse
import collections
import io
import json
import os
import sys

READY_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")

# ── Re-use ClaudePlayerEngine from claude_player ─────────────────────────────
from claude_player import ClaudePlayerEngine, _patch_kernel

# ── Scoring constants (mirror scoring.py) ────────────────────────────────────
ICR_STRESS_DELTA   = 0.02
ICR_MINIMUM        = 1.25
ICR_STRESS_YEARS   = 2
LTV_BUFFER_LOW     = 0.60
LTV_BUFFER_HIGH    = 0.75
LTV_CRASH_SEVERITY = 0.20
LTV_LOW_PENALTY    = 0.05
CONC_THRESHOLD     = 0.60
CONC_SEVERITY      = 0.10
EPC_DISCOUNT       = 0.15


def _verify_score(actor, properties, macro_rate, reported):
    """Independently recompute final_score and risk breakdown, return (ok, diff, detail)."""
    prop_map = {p.id: p for p in properties}
    held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]

    equity = sum(p.current_value - p.mortgage_balance for p in held)
    total_return = equity + actor.cash - actor.initial_wealth

    total_value    = sum(p.current_value for p in held) if held else 0
    total_mortgage = sum(p.mortgage_balance for p in held) if held else 0
    annual_rent    = sum(p.rent * 12 for p in held) if held else 0
    leveraged      = [p for p in held if p.mortgage_balance > 0]

    stressed_annual_interest = sum(
        p.mortgage_balance * (p.mortgage_rate + ICR_STRESS_DELTA) for p in leveraged
    )
    if stressed_annual_interest > 0:
        stressed_icr = annual_rent / stressed_annual_interest
        if stressed_icr < ICR_MINIMUM:
            icr_cost = (stressed_annual_interest * ICR_MINIMUM - annual_rent) * ICR_STRESS_YEARS
        else:
            icr_cost = 0.0
    else:
        icr_cost = 0.0

    ltv = total_mortgage / total_value if total_value > 0 else 0.0
    if ltv > LTV_BUFFER_HIGH:
        ltv_cost = total_value * LTV_CRASH_SEVERITY * min(1.0, (ltv - LTV_BUFFER_HIGH) / (1.0 - LTV_BUFFER_HIGH))
    elif ltv > LTV_BUFFER_LOW:
        ltv_cost = total_value * LTV_LOW_PENALTY * (ltv - LTV_BUFFER_LOW) / (LTV_BUFFER_HIGH - LTV_BUFFER_LOW)
    else:
        ltv_cost = 0.0

    region_values = {}
    for p in held:
        region_values[p.region] = region_values.get(p.region, 0) + p.current_value
    max_region_pct = max(region_values.values()) / total_value if total_value > 0 else 1.0
    conc_cost = (total_value * CONC_SEVERITY * (max_region_pct - CONC_THRESHOLD) / (1.0 - CONC_THRESHOLD)
                 if max_region_pct > CONC_THRESHOLD else 0.0)

    non_compliant_value = sum(p.current_value for p in held if p.epc_band >= 4)
    epc_cost = non_compliant_value * EPC_DISCOUNT

    risk_cost   = round(icr_cost + ltv_cost + conc_cost + epc_cost, 0)
    computed    = round(total_return - risk_cost, 0)
    diff        = computed - reported
    ok          = abs(diff) < 2   # allow £1 rounding tolerance

    detail = (f"equity={equity:,.0f} cash={actor.cash:,.0f} init={actor.initial_wealth:,.0f} "
              f"total_return={total_return:,.0f} risk={risk_cost:,.0f} "
              f"icr={icr_cost:,.0f} ltv={ltv_cost:,.0f} conc={conc_cost:,.0f} epc={epc_cost:,.0f}")
    return ok, diff, detail


_log_file = None

def _log(msg):
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()


def run_game(game_num, turns, SimulationKernel):
    kernel = SimulationKernel(turns=turns, mode="student", turn_delay=0)
    kernel.player_choices = ClaudePlayerEngine()

    player      = kernel.state.actors["player"]
    prop_map_0  = {p.id: p for p in kernel.state.properties}
    actor_names = {aid: a.name for aid, a in kernel.state.actors.items()}
    actor_names["player"] = "You"

    # Identify leverage actor for this game (may not exist)
    leverage_actor_id = next(
        (aid for aid, a in kernel.state.actors.items() if a.strategy == "leverage"), None
    )

    _log(f"\n{'='*72}")
    _log(f"GAME {game_num}  |  {turns} turns  |  era: {kernel.era_label}")
    _log(f"{'='*72}")
    _log(f"  Players: " + "  |  ".join(
        f"{aid}={a.name}[{a.strategy}]" for aid, a in kernel.state.actors.items()))
    _log(f"  Starting cash: player=£{player.cash:,.0f}")
    _log(f"  Starting portfolio:")
    for pid in player.portfolio:
        p = prop_map_0[pid]
        _log(f"    {pid}  {p.region:<22} £{p.current_value:>9,.0f}  "
             f"yield={p.rent*12/p.current_value:.1%}  EPC={chr(64+p.epc_band)}  arch={p.archetype}")

    # Collect buy records per actor for property comparison
    buy_records = collections.defaultdict(list)  # actor_id -> list of property metadata

    original_write = kernel._write_turn_state

    def logged_write(tick_events_arg, *args, is_final=False):
        tick = kernel.state.tick
        if tick > 0:
            # Derive year label from historical slice (index = tick-1)
            year, half, *_ = kernel.historical_slice[tick - 1]
            year_label = f"{year} H{half}"

            pm = {p.id: p for p in kernel.state.properties}

            # Log all actor actions with year label
            for ev in tick_events_arg:
                if ev.get("type") not in ("player_action", "ai_action"):
                    continue
                aid    = ev.get("actor_id", "?")
                action = ev.get("action", "hold")
                pid    = ev.get("property_id") or ""
                ltv    = ev.get("ltv", 0.0)
                name   = actor_names.get(aid, aid)

                prop = pm.get(pid)
                prop_detail = ""
                if prop and action == "buy":
                    gross_yield = prop.rent * 12 / prop.current_value if prop.current_value else 0
                    prop_detail = (f"  arch={prop.archetype}  region={prop.region}"
                                   f"  value=£{prop.current_value:,.0f}"
                                   f"  yield={gross_yield:.1%}  EPC={chr(64+prop.epc_band)}")
                    buy_records[aid].append({
                        "game": game_num, "tick": tick, "year": year_label,
                        "pid": pid, "archetype": prop.archetype, "region": prop.region,
                        "value": prop.current_value,
                        "gross_yield": gross_yield,
                        "epc_band": prop.epc_band,
                        "ltv": ltv,
                    })

                act_obj = kernel.state.actors.get(aid)
                portfolio_now = act_obj.portfolio if act_obj else []
                if   action == "buy":     ok = pid in portfolio_now
                elif action == "sell":    ok = pid not in portfolio_now
                else:                     ok = True
                status = "OK" if ok else "FAILED"

                _log(f"  {year_label}  {name:<20}  {action:<8} {pid:<7} ltv={ltv:.0%}"
                     f"  [{status}]{prop_detail}")

        original_write(tick_events_arg, *args, is_final=is_final)

    kernel._write_turn_state = logged_write

    results = kernel.run()
    lb = results["leaderboard"]

    _log(f"\n  LEADERBOARD (game {game_num}):")
    score_checks = []
    for rank, entry in enumerate(lb, 1):
        marker = " <--" if entry["actor_id"] == "player" else ""
        _log(f"    {rank}. {entry['name']:<22}"
             f"  score=£{entry['final_score']:>12,.0f}"
             f"  equity=£{entry['portfolio_value']:>10,.0f}"
             f"  cash=£{entry['cash']:>10,.0f}{marker}")

        # Verify score
        actor = kernel.state.actors[entry["actor_id"]]
        ok, diff, detail = _verify_score(
            actor, kernel.state.properties,
            kernel.state.macro.interest_rate,
            entry["final_score"],
        )
        status = "OK" if ok else f"MISMATCH diff=£{diff:+,.0f}"
        _log(f"       score_check: {status}  |  {detail}")
        score_checks.append(ok)

    all_ok = all(score_checks)
    _log(f"  Score verification: {'ALL OK' if all_ok else 'FAILURES DETECTED'}")

    player_rank = next((i + 1 for i, e in enumerate(lb) if e["actor_id"] == "player"), 3)
    player_score = next((e["final_score"] for e in lb if e["actor_id"] == "player"), 0)

    return lb, player_rank, player_score, kernel.era_label, buy_records, leverage_actor_id, all_ok


def main():
    global _log_file

    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=20)
    parser.add_argument("--games", type=int, default=33)
    parser.add_argument("--log",   type=str, default="results_analysis.txt")
    args = parser.parse_args()

    if args.log:
        _log_file = open(args.log, "w", encoding="utf-8")

    os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)

    import kernel as kernel_module
    from kernel import SimulationKernel

    _patch_kernel(kernel_module)

    game_summaries   = []
    all_buy_records  = collections.defaultdict(list)
    all_score_ok     = True
    lever_games      = 0

    for g in range(1, args.games + 1):
        lb, rank, score, era, buy_records, lever_id, score_ok = run_game(
            g, args.turns, SimulationKernel)
        if not score_ok:
            all_score_ok = False
        for aid, recs in buy_records.items():
            all_buy_records[aid].extend(recs)
        if lever_id:
            lever_games += 1
        player_entry = next((e for e in lb if e["actor_id"] == "player"), {})
        game_summaries.append({
            "game": g, "era": era, "rank": rank, "score": score,
            "lever_id": lever_id,
        })

    # ── Cross-game summary ────────────────────────────────────────────────────
    _log(f"\n\n{'='*72}")
    _log(f"SUMMARY — {args.games} games x {args.turns} turns")
    _log(f"{'='*72}")
    _log(f"\nScore verification across all games: {'ALL OK' if all_score_ok else 'FAILURES DETECTED'}")

    _log(f"\nPer-game results:")
    _log(f"  {'Game':<6} {'Era':<42} {'Rank':<6} {'Score':>14}  Lever?")
    wins = 0
    for s in game_summaries:
        if s["rank"] == 1:
            wins += 1
        lever = "yes" if s["lever_id"] else "no"
        _log(f"  {s['game']:<6} {s['era']:<42} {s['rank']:<6} £{s['score']:>12,.0f}  {lever}")
    avg_score = sum(s["score"] for s in game_summaries) / len(game_summaries)
    avg_rank  = sum(s["rank"]  for s in game_summaries) / len(game_summaries)
    _log(f"\n  Avg score: £{avg_score:,.0f}   Avg rank: {avg_rank:.1f}/3   Wins: {wins}/{args.games}")
    _log(f"  Games with Mr Max Lever (leverage): {lever_games}/{args.games}")

    # ── Property comparison: player vs leverage ───────────────────────────────
    _log(f"\n\n{'='*72}")
    _log(f"PROPERTY COMPARISON: Player vs leverage AI (Mr Max Lever)")
    _log(f"{'='*72}")

    def _summarise_buys(recs, label):
        if not recs:
            _log(f"\n{label}: no buy records")
            return
        n = len(recs)
        avg_value = sum(r["value"] for r in recs) / n
        avg_yield = sum(r["gross_yield"] for r in recs) / n
        avg_epc   = sum(r["epc_band"] for r in recs) / n
        avg_ltv   = sum(r["ltv"] for r in recs) / n

        arch_counts  = collections.Counter(r["archetype"] for r in recs)
        region_counts = collections.Counter(r["region"] for r in recs)

        _log(f"\n{label}  (n={n} buys across games where present)")
        _log(f"  Avg value:      £{avg_value:>10,.0f}")
        _log(f"  Avg gross yield: {avg_yield:.1%}")
        _log(f"  Avg EPC band:    {avg_epc:.1f}  ({chr(64+round(avg_epc))} on average)")
        _log(f"  Avg LTV used:    {avg_ltv:.0%}")
        _log(f"  Archetype mix:")
        for arch, cnt in arch_counts.most_common():
            _log(f"    {arch:<12} {cnt:>4}  ({cnt/n*100:.0f}%)")
        _log(f"  Top 5 regions:")
        for region, cnt in region_counts.most_common(5):
            _log(f"    {region:<25} {cnt:>4}  ({cnt/n*100:.0f}%)")
        yield_buckets = collections.Counter(
            "<5%" if r["gross_yield"] < 0.05 else
            "5-7%" if r["gross_yield"] < 0.07 else
            "7-10%" if r["gross_yield"] < 0.10 else "10%+"
            for r in recs
        )
        _log(f"  Yield distribution:")
        for bucket in ["<5%", "5-7%", "7-10%", "10%+"]:
            cnt = yield_buckets[bucket]
            _log(f"    {bucket:<8} {cnt:>4}  ({cnt/n*100:.0f}%)")
        value_buckets = collections.Counter(
            "<£100k" if r["value"] < 100_000 else
            "£100-200k" if r["value"] < 200_000 else
            "£200-350k" if r["value"] < 350_000 else
            "£350k+" for r in recs
        )
        _log(f"  Value distribution:")
        for bucket in ["<£100k", "£100-200k", "£200-350k", "£350k+"]:
            cnt = value_buckets[bucket]
            _log(f"    {bucket:<12} {cnt:>4}  ({cnt/n*100:.0f}%)")

    _summarise_buys(all_buy_records.get("player", []), "PLAYER (balanced/yield-filtered)")

    # Aggregate all leverage actor records (actor_id varies per game)
    lever_recs = []
    for aid, recs in all_buy_records.items():
        if aid not in ("player", "ai1", "ai2"):
            continue
        # We tagged the leverage actor id per game; match via game+actor cross
    # Rebuild lever records using stored lever_id per game
    for s in game_summaries:
        lid = s["lever_id"]
        if lid:
            lever_recs.extend(r for r in all_buy_records.get(lid, []) if r["game"] == s["game"])

    _summarise_buys(lever_recs, f"MR MAX LEVER (leverage, appeared in {lever_games} games)")

    if _log_file:
        _log_file.close()
        print(f"\nFull log: {args.log}")


if __name__ == "__main__":
    main()
