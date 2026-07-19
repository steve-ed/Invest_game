"""
era_analysis.py — Best strategy per 10-year start year (1984–2014).

Method:
  For each start year, pin the kernel to that year and run N games.
  Count wins per strategy. The best strategy is the one with the
  highest win/game% across those N runs.

Grading approach:
  - We fix start_year and randomise start_half (H1/H2) and actor roster
    on each game, so we sample both halves of each year and all strategy
    pairings, not just one fixed combination.
  - 30 games per year × 31 years = 930 games total.
  - Win/game% = wins / games_where_strategy_appeared (not wins/30),
    because the roster is randomised (2-3 AIs per game) and not every
    strategy appears in every game.
"""

import collections, random, sys, os

import kernel as kernel_module
from kernel import SimulationKernel, _select_era
from claude_player import ClaudePlayerEngine, _patch_kernel
from data.uk_macro_history import get_start_limits

_patch_kernel(kernel_module)

GAMES_PER_YEAR = 30
TURNS = 20

def run_pinned(start_year, turns):
    """Run one game pinned to start_year; return (winner_strat, roster_strats)."""
    # Monkey-patch _select_era for this call only
    import kernel as km
    original = km._select_era
    km._select_era = lambda t: (start_year, random.choice([1, 2]))
    try:
        k = SimulationKernel(turns=turns, mode="student", turn_delay=0)
        k.player_choices = ClaudePlayerEngine()
        k._write_turn_state = lambda *a, **kw: None
        results = k.run()
        lb = results["leaderboard"]
        winner_strat = next(
            (k.state.actors[e["actor_id"]].strategy
             for e in lb[:1] if e["actor_id"] in k.state.actors),
            "player" if lb and lb[0]["actor_id"] == "player" else "?"
        )
        roster = {a.strategy if aid != "player" else "player"
                  for aid, a in k.state.actors.items()}
        return winner_strat, roster
    finally:
        km._select_era = original

min_year, max_year = get_start_limits(TURNS)
years = range(min_year, max_year + 1)

print(f"Running {GAMES_PER_YEAR} games × {len(list(years))} years = "
      f"{GAMES_PER_YEAR * len(list(years))} total games...\n")

results = {}  # year -> {strat: {wins, appearances}}

for year in years:
    tally = collections.defaultdict(lambda: {"wins": 0, "appearances": 0})
    for _ in range(GAMES_PER_YEAR):
        winner, roster = run_pinned(year, TURNS)
        for strat in roster:
            tally[strat]["appearances"] += 1
        tally[winner]["wins"] += 1
    results[year] = dict(tally)
    # Quick per-year summary
    ranked = sorted(
        [(s, d["wins"], d["appearances"]) for s, d in tally.items() if s != "player"],
        key=lambda x: -x[1]/x[2] if x[2] else 0,
    )
    best = ranked[0] if ranked else ("?", 0, 0)
    print(f"  {year}: best={best[0]:<14} {best[1]}/{best[2]} games  "
          + "  ".join(f"{s}:{w}/{a}" for s,w,a in ranked[1:3]),
          flush=True)

# ── Final table ──────────────────────────────────────────────────────────────
STRATS = ["capital","demographic","leverage","brrr","value_add","yield"]

print(f"\n{'─'*100}")
print(f"  {'Year':<6} {'Period':<20} {'Best':<14} {'Wpg%':>6}  "
      + "  ".join(f"{s[:7]:>7}" for s in STRATS))
print(f"  {'─'*95}")

for year in years:
    tally = results[year]
    period = f"{year}–{year+9}"
    wpg = {}
    for s in STRATS:
        d = tally.get(s, {"wins":0,"appearances":0})
        wpg[s] = d["wins"]/d["appearances"]*100 if d["appearances"] else 0
    best_s = max(STRATS, key=lambda s: wpg[s])
    best_pct = wpg[best_s]
    print(f"  {year:<6} {period:<20} {best_s:<14} {best_pct:>5.0f}%  "
          + "  ".join(f"{wpg[s]:>6.0f}%" for s in STRATS))

print(f"\nDone.")
