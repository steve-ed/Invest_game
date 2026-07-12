"""
Stacked bar chart: strategy rank position by investment start year (1983–2014).
  - Best strategy occupies the top segment of each bar.
  - Above: 10-year window macro averages on the same x-axis scale.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from data.uk_macro_history import UK_MACRO

WINDOW = 20  # semi-annual = 10 years

# ── Macro metrics ─────────────────────────────────────────────────────────────
def window_metrics_n(start_idx, n=WINDOW):
    data = UK_MACRO[start_idx:start_idx + n]
    hpi_s, hpi_e = data[0][2], data[-1][2]
    hpi_r = (hpi_e - hpi_s) / hpi_s

    rates = [e[3] for e in data]
    rents = [e[4] for e in data]

    avg_rate   = np.mean(rates) / 100
    rate_chg   = (rates[-1] - rates[0]) / 100
    rate_vol   = np.std(rates) / 100
    avg_rent   = np.mean(rents) / 100

    hpi_chg = [(data[i][2] - data[i-1][2]) / data[i-1][2] for i in range(1, len(data))]
    hpi_vol = np.std(hpi_chg)

    return dict(
        hpi_r    = hpi_r,
        rent_g   = avg_rent * 10,
        rate     = avg_rate * 10,
        rate_chg = rate_chg * 10,
        rate_vol = rate_vol * 10,
        hpi_vol  = hpi_vol * 10,
        # raw averages for macro panel
        raw_hpi_pct  = (hpi_e - hpi_s) / hpi_s * 100,
        raw_avg_rate = np.mean(rates),
        raw_avg_rent = np.mean(rents),
    )

# ── Strategy scoring ──────────────────────────────────────────────────────────
STRAT_NAMES = [
    "Yield-Focused", "Capital-Growth", "Value-Add", "BRRR",
    "Leverage-Optimised", "Diversification", "Regulation-Arb.",
    "Demographic-Trend", "Short-Let", "HMO",
]
STRAT_COLORS = [
    "#e74c3c", "#ecad0a", "#27ae60", "#3498db", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
]
COLOR_MAP = dict(zip(STRAT_NAMES, STRAT_COLORS))

def score(m, name):
    h, rg, r, rc, rv, hv = (
        m["hpi_r"], m["rent_g"], m["rate"],
        m["rate_chg"], m["rate_vol"], m["hpi_vol"],
    )
    return {
        "Yield-Focused":      0.55*rg - 0.35*r  + 0.10*h,
        "Capital-Growth":     0.75*h  + 0.15*rg - 0.10*r,
        "Value-Add":          0.45*h  + 0.35*rg - 0.20*r,
        "BRRR":               0.55*h  + 0.10*rg - 0.25*r  - 0.20*rc,
        "Leverage-Optimised": 0.65*h  - 0.15*r  - 0.20*rc,
        "Diversification":    0.35*h  + 0.35*rg - 0.15*r  - 0.15*hv,
        "Regulation-Arb.":   0.35*h  + 0.40*rg - 0.25*rv,
        "Demographic-Trend":  0.60*h  + 0.25*rg - 0.15*r,
        "Short-Let":          0.15*h  + 0.65*rg - 0.20*r,
        "HMO":                0.05*h  + 0.70*rg - 0.25*r,
    }[name]

# ── Build data ────────────────────────────────────────────────────────────────
# Pre-compute cumulative inflation index (1983 H1 = 100) for every entry
cum_inf_by_idx = []
_cum = 100.0
for e in UK_MACRO:
    _cum *= (1 + e[5] / 100 / 2)
    cum_inf_by_idx.append(_cum)

start_years, hpi_pcts, avg_rates, avg_rents, cum_infs, window_sizes = [], [], [], [], [], []
# ranked_by_pos[year_idx][pos] = strategy name  (pos 0 = rank 10/worst, pos 9 = rank 1/best)
ranked_by_pos = []

for i, entry in enumerate(UK_MACRO):
    if entry[1] != 1:
        continue
    available = len(UK_MACRO) - i
    if available < 2:          # need at least 1 full period
        break

    win = min(WINDOW, available)
    m = window_metrics_n(i, win)
    scores = {s: score(m, s) for s in STRAT_NAMES}
    ordered = sorted(STRAT_NAMES, key=lambda s: scores[s])  # worst → best

    start_years.append(entry[0])
    hpi_pcts.append(entry[2])
    avg_rates.append(entry[3])
    avg_rents.append(entry[4])
    cum_infs.append(cum_inf_by_idx[i])
    window_sizes.append(win // 2)     # in years
    ranked_by_pos.append(ordered)

n = len(start_years)

# ── Figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(26, 13))
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 2.8], hspace=0.08)

ax_macro = fig.add_subplot(gs[0])
ax_bar   = fig.add_subplot(gs[1], sharex=ax_macro)

BAR_WIDTH = 0.72

# ── Top panel: macro indicators ───────────────────────────────────────────────
ax_macro.set_title(
    "Investment Strategy Rankings by Start Year  (10-year windows 1983–2015; shorter windows 2016–2024)",
    fontsize=12, fontweight="bold", pad=10,
)

ax2 = ax_macro.twinx()

# Raise ax2 above ax_macro so its lines render over the era band fills
ax2.set_zorder(ax_macro.get_zorder() + 1)
ax_macro.patch.set_visible(False)

ln1, = ax_macro.plot(start_years, hpi_pcts,  color="#ecad0a", lw=2.2,
                     marker="o", ms=4, zorder=5, label="HPI index (1983=100)")
ln4, = ax_macro.plot(start_years, cum_infs,  color="#ff6b9d", lw=1.8,
                     marker="", linestyle="--", zorder=5, label="Cumulative inflation (1983=100)")
ln2, = ax2.plot(start_years, avg_rates, color="#e74c3c",  lw=2.2,
                marker="s", ms=4, zorder=6, label="BoE base rate % (at start year)")
ln3, = ax2.plot(start_years, avg_rents, color="#2ecc71",  lw=2.0,
                marker="^", ms=3.5, linestyle="--", zorder=6, label="Rent growth % pa (at start year)")

left_max = max(max(hpi_pcts), max(cum_infs)) * 1.12
ax_macro.set_ylim(0, left_max)
right_max = max(max(avg_rates), max(avg_rents)) * 1.2
ax2.set_ylim(0, right_max)

ax_macro.set_ylabel("Index (1983 H1 = 100)", color="#888888", fontsize=9)
ax2.set_ylabel("Rate / rent growth %", color="#555555", fontsize=9)
ax_macro.tick_params(axis="y", labelcolor="#888888")
ax_macro.grid(axis="y", alpha=0.2)
ax_macro.tick_params(axis="x", which="both", bottom=False, labelbottom=False)

all_lines = [ln1, ln4, ln2, ln3]
ax_macro.legend(all_lines, [l.get_label() for l in all_lines],
                loc="upper left", fontsize=8, framealpha=0.85)

# ── Bottom panel: stacked bar ─────────────────────────────────────────────────
for j in range(n):
    yr = start_years[j]
    for pos, strat in enumerate(ranked_by_pos[j]):   # pos 0 = worst (bottom)
        ax_bar.bar(yr, 1, bottom=pos, width=BAR_WIDTH,
                   color=COLOR_MAP[strat], edgecolor="white", linewidth=0.3, zorder=3)

# Y-axis: rank labels (bottom = 10th/worst, top = 1st/best)
ax_bar.set_ylim(0, 10)
ax_bar.set_yticks([i + 0.5 for i in range(10)])
ax_bar.set_yticklabels(
    ["10th (worst)", "9th", "8th", "7th", "6th", "5th", "4th", "3rd", "2nd", "1st (best)"],
    fontsize=7.5,
)
ax_bar.set_ylabel("Strategy rank position", fontsize=9)
ax_bar.grid(axis="y", alpha=0.2, zorder=0)

# X-axis — label every 2 years to avoid clashing
ax_bar.set_xticks(start_years)
ax_bar.set_xticklabels(
    [str(y) if y % 2 == 1 else "" for y in start_years],
    rotation=45, ha="right", fontsize=8,
)
ax_bar.set_xlabel(
    "Investment start year  "
    "(10-year assessment window 1983–2015; windows shorten progressively from 2016 as data approaches 2024 H2)",
    fontsize=9,
)

# Horizontal dividers at each rank boundary
for k in range(1, 10):
    ax_bar.axhline(k, color="white", lw=0.6, zorder=4)

# Shade era backgrounds on both panels
era_bands = [
    (1982.5, 1988.5, "#fff9e6", "Late Thatcher boom"),
    (1988.5, 1993.5, "#fdecea", "Crash & bust"),
    (1993.5, 2000.5, "#eafaf1", "Mid-90s recovery"),
    (2000.5, 2007.5, "#e8f4fd", "Long boom / pre-GFC"),
    (2007.5, 2014.5, "#f4ecf7", "GFC & austerity"),
    (2014.5, 2020.5, "#fef9e7", "Sustained growth & Brexit"),
    (2020.5, 2024.5, "#fdf2f8", "COVID surge & rate shock"),
]
for x0, x1, col, label in era_bands:
    for ax in (ax_macro, ax_bar):
        ax.axvspan(x0, x1, color=col, alpha=0.55, zorder=0)
    ax_bar.text((x0 + x1) / 2, 10.15, label,
                ha="center", va="bottom", fontsize=7, color="#555555",
                style="italic", clip_on=False)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color=COLOR_MAP[s], label=s) for s in STRAT_NAMES
]
ax_bar.legend(
    handles=legend_patches, loc="lower right",
    fontsize=7.5, framealpha=0.92, ncol=2,
    title="Strategy  (colour)", title_fontsize=8,
)

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "strategy_stacked.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {os.path.abspath(out)}")
