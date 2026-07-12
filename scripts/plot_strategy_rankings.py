"""
Strategy ranking by 10-year investment window (1983–2014 start years).

Scoring logic: each strategy is assigned a weighted score from macro metrics
computed over its 10-year (20 semi-annual) window. Strategies are ranked 1–10
within each period (1 = best). Higher score = better outcome.

Macro inputs used:
  hpi_r       : total HPI return over window (fractional)
  rent_g      : mean annualised rent growth (decimal, ×10 to approximate 10yr cumulative)
  rate        : mean BoE base rate (decimal, ×10 as 10yr cost proxy)
  rate_chg    : end_rate − start_rate (decimal, negative = rates fell = refinancing benefit)
  rate_vol    : std dev of rates (decimal, proxy for regulatory/macro instability)
  hpi_vol     : std dev of semi-annual HPI changes (fractional, downside risk proxy)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from data.uk_macro_history import UK_MACRO

WINDOW = 20  # semi-annual periods = 10 years


def window_metrics(start_idx):
    data = UK_MACRO[start_idx:start_idx + WINDOW]
    hpi_s, hpi_e = data[0][2], data[-1][2]
    hpi_r = (hpi_e - hpi_s) / hpi_s

    rates = [e[3] for e in data]
    rents = [e[4] for e in data]

    avg_rate   = np.mean(rates) / 100
    rate_chg   = (rates[-1] - rates[0]) / 100
    rate_vol   = np.std(rates) / 100
    avg_rent   = np.mean(rents) / 100

    hpi_chg    = [(data[i][2] - data[i-1][2]) / data[i-1][2] for i in range(1, len(data))]
    hpi_vol    = np.std(hpi_chg)

    # Scale rent and rate to 10-year equivalents so they're comparable to hpi_r
    return dict(
        hpi_r    = hpi_r,
        rent_g   = avg_rent * 10,
        rate     = avg_rate * 10,
        rate_chg = rate_chg * 10,
        rate_vol = rate_vol * 10,
        hpi_vol  = hpi_vol * 10,
    )


# Strategy scoring functions — higher score = better outcome for that strategy.
# Negative rate_chg means rates fell (good for leveraged / refinancing plays).
STRATEGIES = {
    "Yield-Focused":      lambda m: 0.55*m["rent_g"] - 0.35*m["rate"]     + 0.10*m["hpi_r"],
    "Capital-Growth":     lambda m: 0.75*m["hpi_r"]  + 0.15*m["rent_g"]   - 0.10*m["rate"],
    "Value-Add":          lambda m: 0.45*m["hpi_r"]  + 0.35*m["rent_g"]   - 0.20*m["rate"],
    "BRRR":               lambda m: 0.55*m["hpi_r"]  + 0.10*m["rent_g"]   - 0.25*m["rate"]    - 0.20*m["rate_chg"],
    "Leverage-Optimised": lambda m: 0.65*m["hpi_r"]  - 0.15*m["rate"]     - 0.20*m["rate_chg"],
    "Diversification":    lambda m: 0.35*m["hpi_r"]  + 0.35*m["rent_g"]   - 0.15*m["rate"]    - 0.15*m["hpi_vol"],
    "Regulation-Arb.":   lambda m: 0.35*m["hpi_r"]  + 0.40*m["rent_g"]   - 0.25*m["rate_vol"],
    "Demographic-Trend":  lambda m: 0.60*m["hpi_r"]  + 0.25*m["rent_g"]   - 0.15*m["rate"],
    "Short-Let":          lambda m: 0.15*m["hpi_r"]  + 0.65*m["rent_g"]   - 0.20*m["rate"],
    "HMO":                lambda m: 0.05*m["hpi_r"]  + 0.70*m["rent_g"]   - 0.25*m["rate"],
}

# ── Build rankings ────────────────────────────────────────────────────────────
start_years = []
rankings = {s: [] for s in STRATEGIES}

for i, entry in enumerate(UK_MACRO):
    if entry[1] != 1:          # H1 starts only
        continue
    if i + WINDOW > len(UK_MACRO):
        break
    year = entry[0]
    if year > 2014:
        break

    m = window_metrics(i)
    scores = {s: fn(m) for s, fn in STRATEGIES.items()}
    sorted_strats = sorted(scores, key=scores.get, reverse=True)
    rank = {s: sorted_strats.index(s) + 1 for s in STRATEGIES}

    start_years.append(year)
    for s in STRATEGIES:
        rankings[s].append(rank[s])

# ── Plot ──────────────────────────────────────────────────────────────────────
COLORS = [
    "#e74c3c", "#ecad0a", "#2ecc71", "#3498db", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
]
STRAT_NAMES = list(STRATEGIES.keys())

fig, ax = plt.subplots(figsize=(16, 7))

# Shade macro era backgrounds
era_bands = [
    (1983, 1988, "#fff9e6", "Late Thatcher boom"),
    (1988, 1993, "#fdecea", "Crash & bust"),
    (1993, 2000, "#eafaf1", "Mid-90s recovery & Labour boom"),
    (2000, 2008, "#e8f4fd", "Long boom / pre-GFC"),
    (2008, 2014, "#f4ecf7", "GFC & austerity starts"),
]
for x0, x1, col, label in era_bands:
    ax.axvspan(x0, x1, color=col, alpha=0.6, zorder=0)
    ax.text((x0 + x1) / 2, 10.35, label, ha="center", va="bottom",
            fontsize=6.5, color="#666666", style="italic")

for i, strat in enumerate(STRAT_NAMES):
    ax.plot(start_years, rankings[strat],
            color=COLORS[i], linewidth=2, marker="o", markersize=3,
            label=strat, zorder=3)

ax.set_xlabel("Investment start year  (10-year window)", fontsize=10)
ax.set_ylabel("Strategy rank  (1 = best)", fontsize=10)
ax.set_title("Investment Strategy Rankings by Start Year  (1983–2014, 10-year windows)",
             fontsize=12, fontweight="bold")

ax.set_ylim(10.7, 0.3)          # rank 1 at top, 10 at bottom
ax.set_yticks(range(1, 11))
ax.set_xticks(start_years)
ax.set_xticklabels(start_years, rotation=45, ha="right", fontsize=8)
ax.grid(axis="y", alpha=0.25)
ax.grid(axis="x", alpha=0.12)

legend = ax.legend(loc="upper right", fontsize=7.5, framealpha=0.9,
                   title="Strategy", title_fontsize=8)

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "strategy_rankings.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {os.path.abspath(out)}")

# ── Print summary table ───────────────────────────────────────────────────────
print(f"\n{'Year':<6}", end="")
for s in STRAT_NAMES:
    print(f"{s[:10]:<12}", end="")
print()
print("-" * (6 + 12 * len(STRAT_NAMES)))
for j, yr in enumerate(start_years):
    print(f"{yr:<6}", end="")
    for s in STRAT_NAMES:
        print(f"{rankings[s][j]:<12}", end="")
    print()
