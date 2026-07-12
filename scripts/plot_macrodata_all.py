import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from data.uk_macro_history import UK_MACRO

labels  = [f"{y} H{h}" for y, h, *_ in UK_MACRO]
hpi     = [e[2] for e in UK_MACRO]
rates   = [e[3] for e in UK_MACRO]
rents   = [e[4] for e in UK_MACRO]

# Cumulative inflation compounded semi-annually
cum_inf, cum_inf_vals = 100.0, []
for e in UK_MACRO:
    cum_inf *= (1 + e[5] / 100 / 2)
    cum_inf_vals.append(cum_inf)

x = range(len(labels))
tick_step = 4  # label every 2 years

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 12), sharex=True)
fig.suptitle("UK Macro History 1983–2024 (semi-annual)", fontsize=14, fontweight="bold")

# ── Top: Price Index & Cumulative Inflation ──────────────────────────────────
ax1.plot(x, hpi, color="#ecad0a", linewidth=2, label="House Price Index (1983=100)")
ax1.plot(x, cum_inf_vals, color="#ff6b9d", linewidth=1.5, linestyle="--", label="Cumulative Inflation (1983=100)")
ax1.set_ylabel("Index (1983 H1 = 100)")
ax1.legend(loc="upper left", fontsize=8)
ax1.grid(axis="y", alpha=0.3)
ax1.set_title("House Price Index & Cumulative Inflation", fontsize=10)

# ── Middle: BoE Base Rate ────────────────────────────────────────────────────
ax2.plot(x, rates, color="#e74c3c", linewidth=2, label="BoE Base Rate (%)")
ax2.fill_between(x, rates, alpha=0.15, color="#e74c3c")
ax2.set_ylabel("Rate (%)")
ax2.legend(loc="upper right", fontsize=8)
ax2.grid(axis="y", alpha=0.3)
ax2.set_title("Bank of England Base Rate", fontsize=10)

# ── Bottom: Rent Growth & CPI ────────────────────────────────────────────────
cpi_vals = [e[5] for e in UK_MACRO]
ax3.plot(x, rents, color="#2ecc71", linewidth=2, label="Rent Growth (% pa)")
ax3.plot(x, cpi_vals, color="#9b59b6", linewidth=1.5, linestyle=":", label="CPI/RPI (% pa)")
ax3.axhline(0, color="gray", linewidth=0.5)
ax3.set_ylabel("% per annum")
ax3.legend(loc="upper right", fontsize=8)
ax3.grid(axis="y", alpha=0.3)
ax3.set_title("Rent Growth & CPI/RPI Inflation", fontsize=10)

# ── X-axis labels ────────────────────────────────────────────────────────────
visible = [i for i in x if i % tick_step == 0]
ax3.set_xticks(visible)
ax3.set_xticklabels([labels[i] for i in visible], rotation=45, ha="right", fontsize=7)

# Annotate key events on price chart
events = {
    "1989 H1": "Peak boom",
    "1992 H2": "Black Wed",
    "2007 H2": "Northern Rock",
    "2008 H2": "Lehman",
    "2020 H2": "COVID surge",
    "2022 H2": "Peak prices",
}
for lbl, note in events.items():
    if lbl in labels:
        i = labels.index(lbl)
        ax1.annotate(note, xy=(i, hpi[i]), xytext=(i+1, hpi[i]+30),
                     fontsize=6.5, color="#555555",
                     arrowprops=dict(arrowstyle="-", color="#aaaaaa", lw=0.8))

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "macrodata_all.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {os.path.abspath(out)}")
