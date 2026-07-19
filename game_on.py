"""
game_on.py — 99-game monitor.

Tracks per-tick for every game:
  - macro:  price index, interest rate, rent growth
  - per actor: property count, portfolio wealth, cash

Usage:
    python game_on.py [--turns 20] [--games 99]

Output:
    game_on_summary.csv   — one row per (game, tick, actor)
    game_on_macro.csv     — one row per (game, tick) for macro
    Prints a per-game leaderboard and a final wins table.
"""

import argparse
import collections
import csv
import os
import sys

READY_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")

from claude_player import ClaudePlayerEngine, _patch_kernel


def run_game(game_num, turns, SimulationKernel):
    kernel = SimulationKernel(turns=turns, mode="student", turn_delay=0)
    kernel.player_choices = ClaudePlayerEngine()
    kernel._write_turn_state = lambda *a, **kw: None

    actor_rows = []   # (game, tick, actor_id, name, strategy, n_props, port_wealth, cash)
    macro_rows = []   # (game, tick, price_index, interest_rate, rent_growth)

    original_run = kernel.run

    def _monitored_run():
        # Replicate the kernel's tick loop but capture state each tick.
        # We call kernel.run() normally but hook _write_turn_state.
        pass

    # Hook into each tick by wrapping _write_turn_state before run()
    orig_write = kernel._write_turn_state

    def _capture(tick_events, *args, is_final=False):
        tick  = kernel.state.tick
        macro = kernel.state.macro
        prop_map = {p.id: p for p in kernel.state.properties}

        macro_rows.append({
            "game":          game_num,
            "tick":          tick,
            "price_index":   round(macro.price_index, 2),
            "interest_rate": round(macro.interest_rate * 100, 3),
            "rent_growth":   round(macro.rent_growth * 100, 3),
        })

        for actor_id, actor in kernel.state.actors.items():
            held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
            port_wealth = sum(p.current_value - p.mortgage_balance for p in held)
            actor_rows.append({
                "game":         game_num,
                "tick":         tick,
                "actor_id":     actor_id,
                "name":         actor.name,
                "strategy":     actor.strategy if actor_id != "player" else "player",
                "n_props":      len(actor.portfolio),
                "port_wealth":  round(port_wealth, 0),
                "cash":         round(actor.cash, 0),
                "final_score":  "",   # filled in after game ends
                "risk_cost":    "",
            })

        orig_write(tick_events, *args, is_final=is_final)

    kernel._write_turn_state = _capture

    start_year  = kernel.state.start_year
    start_half  = kernel.state.start_half
    actor_roster = {aid: a.strategy if aid != "player" else "player"
                    for aid, a in kernel.state.actors.items()}

    results = kernel.run()
    lb = results["leaderboard"]

    # Back-fill final_score and risk_cost into every row for this game
    score_map = {e["actor_id"]: (e.get("final_score", 0), e.get("risk_cost", 0)) for e in lb}
    for row in actor_rows:
        fs, rc = score_map.get(row["actor_id"], ("", ""))
        row["final_score"] = fs
        row["risk_cost"]   = rc

    winner = lb[0]["name"] if lb else "?"
    winner_score = lb[0]["final_score"] if lb else 0
    player_entry = next((e for e in lb if e["actor_id"] == "player"), {})
    player_rank  = next((i + 1 for i, e in enumerate(lb) if e["actor_id"] == "player"), "-")
    player_score = player_entry.get("final_score", 0)

    print(
        f"  Game {game_num:>3}  {start_year}H{start_half}  era={kernel.era_label[:28]:<28}  "
        f"winner={winner:<22}  £{winner_score:>10,.0f}  "
        f"you=rank{player_rank} £{player_score:>10,.0f}",
        flush=True,
    )

    return lb, actor_rows, macro_rows, kernel.era_label, start_year, start_half, actor_roster


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=20)
    parser.add_argument("--games", type=int, default=99)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)

    import kernel as kernel_module
    from kernel import SimulationKernel
    _patch_kernel(kernel_module)

    all_actor_rows = []
    all_macro_rows = []
    all_lb         = []
    game_meta      = []   # per-game: start_year, start_half, winner, actor roster
    wins           = collections.Counter()
    seconds        = collections.Counter()
    appearances    = collections.Counter()

    print(f"Running {args.games} games x {args.turns} turns...\n")

    for g in range(1, args.games + 1):
        lb, actor_rows, macro_rows, era, start_year, start_half, roster = \
            run_game(g, args.turns, SimulationKernel)
        all_actor_rows.extend(actor_rows)
        all_macro_rows.extend(macro_rows)
        all_lb.append((g, lb))
        winner_name  = lb[0]["name"]      if len(lb) > 0 else "?"
        winner_id    = lb[0]["actor_id"]  if len(lb) > 0 else "?"
        winner_strat = roster.get(winner_id, "?")
        second_name  = lb[1]["name"]      if len(lb) > 1 else "?"
        second_id    = lb[1]["actor_id"]  if len(lb) > 1 else "?"
        second_strat = roster.get(second_id, "?")
        wins[winner_name] += 1
        seconds[second_name] += 1
        for strategy in roster.values():
            appearances[strategy] += 1
        game_meta.append({
            "game":         g,
            "start_year":   start_year,
            "start_half":   start_half,
            "era":          era,
            "winner_name":  winner_name,
            "winner_strat": winner_strat,
            "second_name":  second_name,
            "second_strat": second_strat,
            "roster":       ",".join(sorted(roster.values())),
        })

    # ── Write CSVs ────────────────────────────────────────────────────────────

    actor_csv = os.path.join(os.path.dirname(__file__), "game_on_actors.csv")
    macro_csv = os.path.join(os.path.dirname(__file__), "game_on_macro.csv")

    with open(actor_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "game", "tick", "actor_id", "name", "strategy",
            "n_props", "port_wealth", "cash", "final_score", "risk_cost",
        ])
        w.writeheader()
        w.writerows(all_actor_rows)

    with open(macro_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "game", "tick", "price_index", "interest_rate", "rent_growth",
        ])
        w.writeheader()
        w.writerows(all_macro_rows)

    meta_csv = os.path.join(os.path.dirname(__file__), "game_on_meta.csv")
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "game", "start_year", "start_half", "era",
            "winner_name", "winner_strat",
            "second_name", "second_strat",
            "roster",
        ])
        w.writeheader()
        w.writerows(game_meta)

    print(f"\nCSVs written:")
    print(f"  {actor_csv}")
    print(f"  {macro_csv}")
    print(f"  {meta_csv}")

    # ── Summary table ─────────────────────────────────────────────────────────

    # Map name -> strategy for the appearances counter display
    name_to_strat = {}
    for m in game_meta:
        name_to_strat[m["winner_name"]] = m["winner_strat"]

    name_to_strat2 = {m["second_name"]: m["second_strat"] for m in game_meta}
    name_to_strat.update(name_to_strat2)

    print(f"\n{'─'*85}")
    print(f"  {'Name':<24} {'Strategy':<14} {'Played':>7}  {'1st':>5}  {'2nd':>5}  {'Top2':>5}  {'1st%':>6}  {'Win/game%':>10}")
    print(f"  {'─'*80}")
    all_names = sorted(
        set(wins) | set(seconds),
        key=lambda n: -(wins.get(n, 0) + seconds.get(n, 0))
    )
    for name in all_names:
        strat   = name_to_strat.get(name, "?")
        played  = appearances.get(strat, 0)
        w       = wins.get(name, 0)
        s       = seconds.get(name, 0)
        win_pct = w / args.games * 100
        wpg     = w / played * 100 if played else 0
        print(f"  {name:<24} {strat:<14} {played:>7}  {w:>5}  {s:>5}  {w+s:>5}  {win_pct:>5.1f}%  {wpg:>9.1f}%")

    # Player rank distribution
    player_ranks = []
    for g, lb in all_lb:
        rank = next((i + 1 for i, e in enumerate(lb) if e["actor_id"] == "player"), None)
        if rank:
            player_ranks.append(rank)

    if player_ranks:
        rank_dist = collections.Counter(player_ranks)
        n = len(player_ranks)
        print(f"\n  Player rank distribution ({n} games):")
        for rank in sorted(rank_dist):
            cnt = rank_dist[rank]
            print(f"    Rank {rank}: {cnt:>4}  ({cnt/n*100:.1f}%)")

    print(f"\nDone — {args.games} games completed.")


if __name__ == "__main__":
    main()
