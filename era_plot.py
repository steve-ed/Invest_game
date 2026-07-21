"""
era_plot.py — Record and plot era analysis results.

Runs 30 pinned games per start year (1984–2014), saves win rates to
era_results.csv, then produces two plots:

  era_heatmap.png  — win-rate heatmap (strategies × years)
  era_winner.png   — winning strategy timeline with win% annotations

Re-uses saved CSV if it exists; pass --rerun to force a fresh simulation.
"""

import argparse
import collections
import csv
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Constants ────────────────────────────────────────────────────────────────

STRATS      = ["capital", "demographic", "leverage", "brrr", "value_add", "yield"]
GAMES_PER_Y = 30
TURNS       = 20
CSV_PATH    = os.path.join(os.path.dirname(__file__), "era_results.csv")

STRAT_COLORS = {
    "capital":     "#FBBF24",   # amber
    "demographic": "#34D399",   # emerald
    "leverage":    "#F87171",   # red
    "brrr":        "#A78BFA",   # purple
    "value_add":   "#60A5FA",   # blue
    "yield":       "#FB923C",   # orange
}

STRAT_LABELS = {
    "capital":     "Capital Growth",
    "demographic": "Demographic",
    "leverage":    "Leverage",
    "brrr":        "BRRR",
    "value_add":   "Value-Add",
    "yield":       "Yield",
}


# ── Simulation ───────────────────────────────────────────────────────────────

def run_simulation():
    import kernel as kernel_module
    from kernel import SimulationKernel
    from claude_player import ClaudePlayerEngine, _patch_kernel
    from data.uk_macro_history import get_start_limits

    _patch_kernel(kernel_module)

    def run_pinned(start_year):
        import kernel as km
        original = km._select_era
        km._select_era = lambda t: (start_year, random.choice([1, 2]))
        try:
            k = SimulationKernel(turns=TURNS, mode="student", turn_delay=0)
            k.player_choices = ClaudePlayerEngine()
            k._write_turn_state = lambda *a, **kw: None
            results = k.run()
            lb = results["leaderboard"]
            winner_strat = next(
                (k.state.actors[e["actor_id"]].strategy
                 for e in lb[:1] if e["actor_id"] in k.state.actors),
                "player" if lb and lb[0]["actor_id"] == "player" else "?",
            )
            roster = {
                a.strategy if aid != "player" else "player"
                for aid, a in k.state.actors.items()
            }
            return winner_strat, roster
        finally:
            km._select_era = original

    min_year, max_year = get_start_limits(TURNS)
    years = range(min_year, max_year + 1)
    rows = []

    print(f"Running {GAMES_PER_Y} games x {len(list(years))} years "
          f"= {GAMES_PER_Y * len(list(years))} games...", flush=True)

    for year in years:
        tally = collections.defaultdict(lambda: {"wins": 0, "appearances": 0})
        for _ in range(GAMES_PER_Y):
            winner, roster = run_pinned(year)
            for s in roster:
                tally[s]["appearances"] += 1
            tally[winner]["wins"] += 1

        row = {"year": year}
        for s in STRATS:
            d = tally.get(s, {"wins": 0, "appearances": 0})
            wpg = d["wins"] / d["appearances"] * 100 if d["appearances"] else 0.0
            row[f"{s}_wins"]        = d["wins"]
            row[f"{s}_appearances"] = d["appearances"]
            row[f"{s}_wpg"]         = round(wpg, 1)

        best = max(STRATS, key=lambda s: row[f"{s}_wpg"])
        row["best"] = best
        rows.append(row)
        print(f"  {year}: best={best:<14} {row[f'{best}_wpg']:.0f}%", flush=True)

    return rows


# ── CSV I/O ──────────────────────────────────────────────────────────────────

def save_csv(rows):
    fieldnames = ["year", "best"] + [
        f"{s}_{m}" for s in STRATS for m in ("wins", "appearances", "wpg")
    ]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved: {CSV_PATH}")


def load_csv():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {"year": int(r["year"]), "best": r["best"]}
            for s in STRATS:
                row[f"{s}_wins"]        = int(r[f"{s}_wins"])
                row[f"{s}_appearances"] = int(r[f"{s}_appearances"])
                row[f"{s}_wpg"]         = float(r[f"{s}_wpg"])
            rows.append(row)
    return rows


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_heatmap(rows):
    years  = [r["year"] for r in rows]
    matrix = np.array([[r[f"{s}_wpg"] for s in STRATS] for r in rows]).T  # (strats, years)

    fig, ax = plt.subplots(figsize=(16, 4))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100,
                   interpolation="nearest")

    ax.set_yticks(range(len(STRATS)))
    ax.set_yticklabels([STRAT_LABELS[s] for s in STRATS], fontsize=9)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=90, fontsize=8)
    ax.set_title("Strategy Win Rate by 10-Year Start (%) — darker = more dominant",
                 fontsize=11, pad=10)

    # Annotate cells with win %
    for yi, s in enumerate(STRATS):
        for xi, year in enumerate(years):
            val = matrix[yi, xi]
            color = "white" if val > 60 else "black"
            if val > 0:
                ax.text(xi, yi, f"{val:.0f}", ha="center", va="center",
                        fontsize=6.5, color=color)

    plt.colorbar(im, ax=ax, label="Win/game %", shrink=0.8)
    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "era_heatmap.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


def plot_winner_timeline(rows):
    years = [r["year"] for r in rows]
    bests = [r["best"] for r in rows]
    wpgs  = [r[f"{r['best']}_wpg"] for r in rows]

    fig, ax = plt.subplots(figsize=(16, 4))

    for i, (year, best, wpg) in enumerate(zip(years, bests, wpgs)):
        color = STRAT_COLORS[best]
        ax.bar(i, wpg, color=color, width=0.85, zorder=2)
        ax.text(i, wpg + 1.5, f"{wpg:.0f}%", ha="center", va="bottom",
                fontsize=6.5, color="black")

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(
        [f"{y}\n–{y+9}" for y in years], rotation=90, fontsize=7
    )
    ax.set_ylabel("Best strategy win rate (%)")
    ax.set_title("Dominant Strategy per 10-Year Period (1984–2014)", fontsize=11)
    ax.set_ylim(0, 115)
    ax.axhline(50, color="#ccc", linewidth=0.8, linestyle="--", zorder=1)
    ax.grid(axis="y", alpha=0.3, zorder=0)

    legend_patches = [
        mpatches.Patch(color=STRAT_COLORS[s], label=STRAT_LABELS[s])
        for s in STRATS
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8,
              ncol=3, framealpha=0.9)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "era_winner.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


def plot_strategy_lines(rows):
    """Line chart: each strategy's win rate across all start years."""
    years = [r["year"] for r in rows]

    fig, ax = plt.subplots(figsize=(16, 5))

    for s in STRATS:
        wpgs = [r[f"{s}_wpg"] for r in rows]
        ax.plot(years, wpgs, color=STRAT_COLORS[s], label=STRAT_LABELS[s],
                linewidth=1.8, marker="o", markersize=3)

    ax.set_xlabel("10-year period start year")
    ax.set_ylabel("Win/game %")
    ax.set_title("Strategy Win Rate Across All 10-Year Start Years", fontsize=11)
    ax.legend(fontsize=9, loc="upper right", ncol=2)
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=90, fontsize=7)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 110)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "era_lines.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true",
                        help="Re-run simulation even if era_results.csv exists")
    args = parser.parse_args()

    if args.rerun or not os.path.exists(CSV_PATH):
        rows = run_simulation()
        save_csv(rows)
    else:
        print(f"Loading existing results from {CSV_PATH}")
        rows = load_csv()

    print(f"\n{'-'*70}")
    print(f"  {'Year':<6} {'Period':<14} {'Best':<14} {'Wpg':>5}  "
          + "  ".join(f"{s[:5]:>5}" for s in STRATS))
    print(f"  {'-'*65}")
    for r in rows:
        best_wpg = r[r["best"] + "_wpg"]
        print(f"  {r['year']:<6} {r['year']}-{r['year']+9:<10} "
              f"{STRAT_LABELS[r['best']]:<14} {best_wpg:>4.0f}%  "
              + "  ".join(f"{r[f'{s}_wpg']:>4.0f}%" for s in STRATS))

    plot_heatmap(rows)
    plot_winner_timeline(rows)
    plot_strategy_lines(rows)
    print("\nDone.")


if __name__ == "__main__":
    main()
