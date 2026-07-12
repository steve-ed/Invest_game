"""
Run N games silently, then plot winner strategy vs start year.
Also reports a filtered subset for games where player, capital and leverage
are all present in the same game.
"""

import collections
import os
import sys

READY_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")

from claude_player import ClaudePlayerEngine, _patch_kernel


def run_game(game_num, turns, SimulationKernel):
    kernel = SimulationKernel(turns=turns, mode="student", turn_delay=0)
    kernel.player_choices = ClaudePlayerEngine()

    player = kernel.state.actors["player"]
    starting_cash = round(player.cash, 0)
    start_year    = kernel.state.start_year
    ai_strategies = {aid: a.strategy for aid, a in kernel.state.actors.items()
                     if aid != "player"}

    kernel._write_turn_state = lambda *a, **kw: None

    results = kernel.run()
    lb = results["leaderboard"]

    def _strategy(actor_id):
        return kernel.state.actors[actor_id].strategy if actor_id != "player" else "player"

    winner_strategy = _strategy(lb[0]["actor_id"])
    second_strategy = _strategy(lb[1]["actor_id"]) if len(lb) > 1 else None
    winner_name     = lb[0]["name"]
    player_rank     = next((i + 1 for i, e in enumerate(lb) if e["actor_id"] == "player"), 3)
    player_score    = next((e["final_score"] for e in lb if e["actor_id"] == "player"), 0)

    print(f"  Game {game_num:>4}  {start_year}  winner={winner_name:<22} [{winner_strategy}]"
          f"  rank={player_rank}  opp={list(ai_strategies.values())}", flush=True)

    return {
        "game":            game_num,
        "start_year":      start_year,
        "era":             kernel.era_label,
        "winner_name":     winner_name,
        "winner_strategy": winner_strategy,
        "second_strategy": second_strategy,
        "player_rank":     player_rank,
        "player_score":    player_score,
        "starting_cash":   starting_cash,
        "ai_strategies":   set(ai_strategies.values()),
    }


def print_stats(records, label=""):
    wins   = collections.Counter(r["winner_strategy"] for r in records)
    second = collections.Counter(r["second_strategy"]  for r in records)
    # appearances = games where this strategy was present (as player or any AI)
    appears = collections.Counter()
    for r in records:
        appears["player"] += 1
        for s in r["ai_strategies"]:
            appears[s] += 1
    all_s  = sorted(set(wins) | set(second) | set(appears), key=lambda s: -wins.get(s, 0))

    print(f"\n{'─'*60}")
    print(f"  {label}  (n={len(records)})")
    print(f"  {'Strategy':<16} {'played':>7}  {'1st':>5}  {'2nd':>5}  {'1st%':>6}  {'top2%':>6}  {'win/game':>9}")
    print(f"  {'─'*56}")
    n = len(records)
    for s in all_s:
        w  = wins.get(s, 0)
        sc = second.get(s, 0)
        ap = appears.get(s, 0)
        win_rate = w / ap * 100 if ap else 0
        print(f"  {s:<16} {ap:>7}  {w:>5}  {sc:>5}  {w/n*100:>5.1f}%  {(w+sc)/n*100:>5.1f}%  {win_rate:>8.1f}%")

    print(f"\n  Player rank distribution:")
    for rank in [1, 2, 3]:
        cnt = sum(1 for r in records if r["player_rank"] == rank)
        print(f"    Rank {rank}: {cnt:>4}  ({cnt/n*100:.1f}%)")


def main():
    turns = 20
    games = 1000

    os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)

    import kernel as kernel_module
    from kernel import SimulationKernel
    _patch_kernel(kernel_module)

    print(f"Running {games} games...", flush=True)
    records = []
    for g in range(1, games + 1):
        rec = run_game(g, turns, SimulationKernel)
        records.append(rec)

    # ── All-games stats ───────────────────────────────────────────────────────
    print_stats(records, "ALL GAMES")

    # ── Filtered: player vs capital vs leverage only ──────────────────────────
    cl_records = [r for r in records
                  if r["ai_strategies"] == {"capital", "leverage"}]
    print_stats(cl_records, "PLAYER vs CAPITAL vs LEVERAGE only")

    print(f"\n  Capital+leverage games: {len(cl_records)} / {games} "
          f"({len(cl_records)/games*100:.1f}%)")
    print(f"\n  Player starting cash range: "
          f"£{min(r['starting_cash'] for r in records):,.0f} – "
          f"£{max(r['starting_cash'] for r in records):,.0f}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.ticker
    import numpy as np

    strategies = ["player", "capital", "leverage", "yield", "brrr", "value_add", "demographic"]
    strategy_labels = {
        "player":      "You (Claude)",
        "capital":     "Mr Hugh Price [capital]",
        "leverage":    "Mr Max Lever [leverage]",
        "yield":       "Ms Di Vidend [yield]",
        "brrr":        "Mr Reid Furbish [brrr]",
        "value_add":   "Mr Ray Novate [value_add]",
        "demographic": "Ms Demi Graphic [demographic]",
    }
    colours = {
        "player":      "#209dd7",
        "capital":     "#e04040",
        "leverage":    "#e07820",
        "yield":       "#2ca02c",
        "brrr":        "#9467bd",
        "value_add":   "#8c564b",
        "demographic": "#e377c2",
    }

    fig, axes = plt.subplots(3, 1, figsize=(16, 14),
                             gridspec_kw={"height_ratios": [3, 2, 1]})
    ax_all, ax_cl, ax_cash = axes

    strat_to_y = {s: i for i, s in enumerate(strategies)}
    rng = np.random.default_rng(42)

    wins_all   = collections.Counter(r["winner_strategy"] for r in records)
    second_all = collections.Counter(r["second_strategy"]  for r in records)
    wins_cl    = collections.Counter(r["winner_strategy"] for r in cl_records)
    second_cl  = collections.Counter(r["second_strategy"]  for r in cl_records)

    xlim = (min(r["start_year"] for r in records) - 1,
            max(r["start_year"] for r in records) + 1)

    def draw_dots(ax, recs, wins, second, title):
        for rec in recs:
            s   = rec["winner_strategy"]
            y   = strat_to_y.get(s, len(strategies))
            jit = rng.uniform(-0.25, 0.25)
            ax.scatter(rec["start_year"], y + jit,
                       color=colours.get(s, "#333"), alpha=0.5, s=40, zorder=3)
        ax.set_yticks(range(len(strategies)))
        ax.set_yticklabels([strategy_labels[s] for s in strategies], fontsize=9)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        ax.set_xlim(xlim)
        n = len(recs)
        for s, y in strat_to_y.items():
            w  = wins.get(s, 0)
            sc = second.get(s, 0)
            ax.text(xlim[1] + 0.3, y,
                    f"{w} ({w/n*100:.0f}%), 2nd {sc}",
                    va="center", fontsize=8, color=colours.get(s, "#333"))

    draw_dots(ax_all, records,    wins_all, second_all,
              f"Winner strategy vs start year — all {games} games")
    draw_dots(ax_cl,  cl_records, wins_cl,  second_cl,
              f"Winner strategy vs start year — Player vs Capital vs Leverage only  (n={len(cl_records)})")

    # Cash panel
    cash_colours = [colours.get(r["winner_strategy"], "#333") for r in records]
    ax_cash.scatter([r["start_year"] for r in records],
                    [r["starting_cash"] for r in records],
                    c=cash_colours, alpha=0.5, s=30, zorder=3)
    ax_cash.set_xlabel("Game start year", fontsize=11)
    ax_cash.set_ylabel("Player starting cash (£)", fontsize=9)
    ax_cash.set_title("Player starting cash by start year  (colour = winner)", fontsize=10)
    ax_cash.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"£{x:,.0f}"))
    ax_cash.grid(alpha=0.3)
    ax_cash.set_xlim(xlim)

    patches = [mpatches.Patch(color=colours[s], label=strategy_labels[s])
               for s in strategies if wins_all.get(s, 0) > 0]
    fig.legend(handles=patches, loc="lower center", ncol=4,
               fontsize=9, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(os.path.dirname(__file__), "wins_by_year.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nPlot saved: {out}")


if __name__ == "__main__":
    main()
