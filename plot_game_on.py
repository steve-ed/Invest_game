"""Plot winner vs start year, actor appearances, and properties per tick."""

import collections
import csv
import os
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

HERE = os.path.dirname(__file__)

# ── Load meta CSV ─────────────────────────────────────────────────────────────

records = []
with open(os.path.join(HERE, "game_on_meta.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        records.append({
            "game":         int(row["game"]),
            "start_year":   int(row["start_year"]),
            "start_half":   int(row["start_half"]),
            "era":          row["era"],
            "winner_name":  row["winner_name"],
            "winner_strat": row["winner_strat"],
            "second_name":  row.get("second_name", "?"),
            "second_strat": row.get("second_strat", "?"),
            "roster":       row["roster"].split(","),
        })

n = len(records)

# ── Load actors CSV — avg n_props per strategy per tick ───────────────────────

# props_by_strat_tick[strategy][tick] = [n_props, ...]
props_by_strat_tick = collections.defaultdict(lambda: collections.defaultdict(list))
with open(os.path.join(HERE, "game_on_actors.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        strat = row["strategy"]
        tick  = int(row["tick"])
        props_by_strat_tick[strat][tick].append(int(row["n_props"]))

all_ticks = sorted({tick for strat in props_by_strat_tick for tick in props_by_strat_tick[strat]})

# ── Colours & actor ordering ──────────────────────────────────────────────────

ACTORS = [
    "You",
    "Mr Hugh Price",
    "Mr Max Lever",
    "Ms Di Vidend",
    "Mr Reid Furbish",
    "Mr Ray Novate",
    "Ms Demi Graphic",
]
STRAT_TO_NAME = {
    "player":      "You",
    "capital":     "Mr Hugh Price",
    "leverage":    "Mr Max Lever",
    "yield":       "Ms Di Vidend",
    "brrr":        "Mr Reid Furbish",
    "value_add":   "Mr Ray Novate",
    "demographic": "Ms Demi Graphic",
}
COLOURS = {
    "You":               "#209dd7",
    "Mr Hugh Price":     "#e04040",
    "Mr Max Lever":      "#e07820",
    "Ms Di Vidend":      "#2ca02c",
    "Mr Reid Furbish":   "#9467bd",
    "Mr Ray Novate":     "#8c564b",
    "Ms Demi Graphic":   "#e377c2",
}

wins        = collections.Counter(r["winner_name"] for r in records)
seconds     = collections.Counter(r["second_name"] for r in records)
appearances = collections.Counter()
for r in records:
    for strat in r["roster"]:
        appearances[strat.strip()] += 1

# ── Figure: two panels ────────────────────────────────────────────────────────

rng = np.random.default_rng(42)
fig, (ax_win, ax_props, ax_app) = plt.subplots(3, 1, figsize=(15, 14),
                                                gridspec_kw={"height_ratios": [3, 2, 1]})

# ── Panel 1: winner vs start year ─────────────────────────────────────────────

actor_to_y = {a: i for i, a in enumerate(ACTORS)}

for r in records:
    # 1st place — filled dot
    w = r["winner_name"]
    y = actor_to_y.get(w, len(ACTORS))
    x = r["start_year"] + (r["start_half"] - 1) * 0.5
    ax_win.scatter(x + rng.uniform(-0.15, 0.15),
                   y + rng.uniform(-0.22, 0.22),
                   color=COLOURS.get(w, "#888"), alpha=0.75, s=55, zorder=3)
    # 2nd place — hollow dot
    s2 = r["second_name"]
    y2 = actor_to_y.get(s2, len(ACTORS))
    ax_win.scatter(x + rng.uniform(-0.15, 0.15),
                   y2 + rng.uniform(-0.22, 0.22),
                   facecolors="none", edgecolors=COLOURS.get(s2, "#888"),
                   alpha=0.55, s=35, linewidths=1.2, zorder=2)

ax_win.set_yticks(range(len(ACTORS)))
ax_win.set_yticklabels(ACTORS, fontsize=11)

x_min = min(r["start_year"] for r in records) - 1
x_max = max(r["start_year"] for r in records) + 1

for actor, y in actor_to_y.items():
    strat  = next((s for s, nm in STRAT_TO_NAME.items() if nm == actor), "?")
    w      = wins.get(actor, 0)
    s2     = seconds.get(actor, 0)
    played = appearances.get(strat, 0)
    wpg    = w / played * 100 if played else 0
    ax_win.text(x_max + 0.3, y,
                f"1st {w}  2nd {s2}  top2 {w+s2}  played {played}  win/game {wpg:.0f}%",
                va="center", fontsize=8.5, color=COLOURS.get(actor, "#888"))

ax_win.set_xlim(x_min, x_max + 16)
ax_win.set_xlabel("Game start year", fontsize=11)
ax_win.set_title(f"Winner by game start year — {n} games", fontsize=13, fontweight="bold")
ax_win.grid(axis="x", alpha=0.3)

# ── Panel 2: avg properties per tick per strategy ────────────────────────────

STRAT_ORDER = ["player", "capital", "leverage", "yield", "brrr", "value_add", "demographic"]

for strat in STRAT_ORDER:
    if strat not in props_by_strat_tick:
        continue
    name   = STRAT_TO_NAME.get(strat, strat)
    colour = COLOURS.get(name, "#888")
    avgs   = [mean(props_by_strat_tick[strat][t]) if t in props_by_strat_tick[strat] else None
              for t in all_ticks]
    valid_ticks = [t for t, v in zip(all_ticks, avgs) if v is not None]
    valid_avgs  = [v for v in avgs if v is not None]
    ax_props.plot(valid_ticks, valid_avgs, color=colour, linewidth=2,
                  label=name, marker="o", markersize=3)

ax_props.set_xlabel("Tick", fontsize=10)
ax_props.set_ylabel("Avg properties held", fontsize=10)
ax_props.set_title("Average number of properties per actor per tick (all 99 games)", fontsize=11, fontweight="bold")
ax_props.legend(fontsize=8, ncol=4, loc="upper left")
ax_props.grid(alpha=0.3)
ax_props.set_xlim(min(all_ticks), max(all_ticks))

# ── Panel 3: appearances bar chart ────────────────────────────────────────────

strats_ordered = [next((s for s, nm in STRAT_TO_NAME.items() if nm == a), a) for a in ACTORS]
bar_counts  = [appearances.get(s, 0) for s in strats_ordered]
bar_colours = [COLOURS.get(STRAT_TO_NAME.get(s, s), "#888") for s in strats_ordered]

bars = ax_app.barh(range(len(ACTORS)), bar_counts, color=bar_colours, alpha=0.8)
ax_app.set_yticks(range(len(ACTORS)))
ax_app.set_yticklabels(ACTORS, fontsize=10)
ax_app.set_xlabel("Games played", fontsize=10)
ax_app.set_title("Actor appearances (games played)", fontsize=11, fontweight="bold")
ax_app.grid(axis="x", alpha=0.3)
for bar, count in zip(bars, bar_counts):
    ax_app.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=9)

# ── Legend & save ─────────────────────────────────────────────────────────────

patches = [mpatches.Patch(color=COLOURS.get(a, "#888"), label=a)
           for a in ACTORS if wins.get(a, 0) > 0 or appearances.get(
               next((s for s, nm in STRAT_TO_NAME.items() if nm == a), ""), 0) > 0]
fig.legend(handles=patches, loc="lower center", ncol=4, fontsize=9,
           bbox_to_anchor=(0.5, -0.02))

plt.tight_layout(rect=[0, 0.04, 1, 1])
out = os.path.join(HERE, "game_on_winners.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Plot saved: {out}")
