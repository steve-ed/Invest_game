# Spec: Real Historical Data Kernel + Educational Dashboard

**Date:** 2026-07-01
**Status:** Approved

## Overview

Replace the synthetic scenario/shock system with real UK historical macro data (1983–2024), and add a live browser-based educational dashboard that updates each turn. The game becomes a playback of a randomly selected 10-year slice of actual UK economic history, with an era label hidden until the end.

---

## 1. Kernel Changes

### Era selection at game start

At `SimulationKernel.__init__`, randomly select a start point from `data/uk_macro_history.UK_MACRO` such that at least `turns` semi-annual entries remain. Use `get_start_limits(turns)` already defined in the data file.

```python
start_year, start_half = random_start(turns)
historical_slice = get_slice(start_year, start_half, turns)
era_label = get_era_label(start_year)  # hidden until end
```

Store `start_year`, `start_half`, `era_label`, and `historical_slice` on the kernel. The era label is passed to `SimulationState` but not exposed to the UI until the end screen.

### Per-turn macro update (replaces ScenarioManager)

Each tick, the kernel reads the next entry from `historical_slice`:

```python
year, half, price_index, rate, rent_growth = historical_slice[tick]
state.macro = MacroState(price_index=price_index, interest_rate=rate, rent_growth=rent_growth)
```

`ScenarioManager.advance()` is no longer called. The current scenario label is derived from the delta direction (see §3 below).

### Property revaluation

`PropertyModel.update()` already scales property values from `price_index`. No change needed — it will work correctly with real data.

---

## 2. State Changes (`state.py`)

Add three fields to `SimulationState`:

| Field | Type | Notes |
|---|---|---|
| `start_year` | `int` | Real calendar year of tick 0 |
| `start_half` | `int` | 1 or 2 |
| `era_label` | `str` | Hidden — only used on end screen |

The UI displays turns as "Year 1, Year 2…" (not real years) to preserve the hidden-era mechanic. The turn badge shows `Turn N / 20`.

---

## 3. Shock Detection (`shocks.py`)

Replace pre-scheduled `Shock` instances with a single function:

```python
def detect_events(prev: MacroSnapshot | None, curr: tuple) -> list[dict]:
```

`prev` is the last `MacroSnapshot` (or `None` on tick 0, in which case no events are fired); `curr` is the new `(year, half, price_index, rate, rent_growth)` tuple. Use `prev.interest_rate` and `prev.price_index` and `prev.rent_growth` for delta computation.

Returns a list of event dicts (same schema as existing event log entries). Detection thresholds:

| Condition | Event type | Student callout |
|---|---|---|
| Rate Δ > +1.5% | `rate_shock_up` | Mortgages get costlier; prices may fall |
| Rate Δ < −1.5% | `rate_shock_down` | Cheaper borrowing; demand lifts prices |
| Rate Δ > +0.5% (smaller) | `rate_rise` | Borrowing costs increasing |
| Rate Δ < −0.5% | `rate_cut` | Borrowing costs easing |
| HPI Δ < −5% | `price_crash` | Market correction; portfolio loses value |
| HPI Δ > +8% | `price_surge` | Boom conditions; hold and ride it |
| Rent Δ > +2% | `rent_surge` | Income growing; landlords benefit |
| Rent Δ < −1% | `rent_squeeze` | Rental income under pressure |

Each event dict: `{"type": <event_type>, "tick": N, "detail": <callout string>, "delta": <float>}`

The scenario label for the turn is derived from the dominant signal:
- HPI falling + rate rising → `"downturn"`
- HPI rising fast → `"boom"`
- Otherwise → `"baseline"`

`scenarios.py` retains its `ScenarioManager` class but is only used for the label string; probabilistic transitions and drift are removed.

---

## 4. Educational Dashboard

### Architecture

A Flask server (`visualisation/dashboard_server.py`) runs as a daemon background thread (so it exits cleanly when the main process ends), started by the kernel at init. Default port is 5050; if unavailable the server tries 5051–5059 and prints the chosen URL. Each turn the kernel writes `visualisation/turn_state.json`. The browser polls `/state` every 1.5 seconds and redraws.

```
kernel.py
  └─ writes → visualisation/turn_state.json  (each tick)
  └─ starts → dashboard_server.py (Flask, background thread, port 5050)
               └─ serves → static/dashboard.html (Chart.js)
               └─ GET /state → returns turn_state.json contents
```

### `turn_state.json` schema

```json
{
  "tick": 8,
  "total_ticks": 20,
  "mode": "student",
  "macro_history": [
    {"tick": 0, "price_index": 152.0, "rate": 8.5, "rent_growth": 5.0},
    ...
  ],
  "wealth_history": [
    {"tick": 0, "player": 1420000, "conservative_ai": 1200000, "aggressive_ai": 1200000},
    ...
  ],
  "events": [
    {"type": "rate_shock_up", "tick": 3, "detail": "Mortgages get costlier; prices may fall", "delta": 2.5}
  ],
  "current_events": [...],
  "scenario": "downturn",
  "actors": {
    "player": {"cash": 200000, "portfolio_value": 1108370, "total": 1308370},
    "conservative_ai": {"cash": 490000, "portfolio_value": 645035, "total": 1135035},
    "aggressive_ai": {"cash": 120000, "portfolio_value": 981180, "total": 1101180}
  },
  "x_labels": ["Y1 H1", "Y1 H2", "Y2 H1", ..., "Y10 H2"],
  "era_label": null
}
```

`era_label` is `null` during play, populated on the final tick only.

### Dashboard layout (`static/dashboard.html`)

Single page, dark theme, two chart rows + callout banner + sidebar:

```
┌─────────────────────────────────────────────────────┬──────────────┐
│ CALLOUT BANNER (event-triggered, one sentence)       │              │
├─────────────────────────────────────────────────────┤   SIDEBAR    │
│ MACRO HISTORY CHART                                  │              │
│ Interest Rate (red) · Price Index (gold) ·           │ Wealth bars  │
│ Rent Growth (green) · shock/scenario markers         │ (current)    │
│ x-axis: Year 1 … Year 10                            │              │
├─────────────────────────────────────────────────────┤ ──────────── │
│ WEALTH CHART                                         │ Event feed   │
│ You (purple) · Conservative AI (blue) ·              │ (last 5)     │
│ Aggressive AI (gold) · dot at current tick           │              │
│ x-axis: same timeline                               │              │
└─────────────────────────────────────────────────────┴──────────────┘
```

**Callout banner:** shown only when `current_events` contains a shock or notable event. Displays the `detail` string from the event. Fades out after 2 turns with no event.

**Shared x-axis:** Both charts use identical tick positions so shock markers (dashed vertical lines) align visually across both.

**Chart.js:** Both charts are `line` type with `animation.duration: 400`. Shock markers are drawn as `annotation` plugin vertical lines.

### Student callout behaviour

The callout banner shows the highest-priority event from `current_events` each tick:
1. `price_crash` or `rate_shock_up` (red — danger)
2. `price_surge` or `rate_shock_down` (green — opportunity)
3. `rent_surge` or `rent_squeeze` (yellow — income)
4. No events → banner hidden

---

## 5. End Screen

On the final tick, `era_label` is populated in `turn_state.json`. The dashboard reveals it in a styled banner:

> **"You played: Late Thatcher Boom (1986–1989)"**
> *Interest rates peaked at 15%. House prices rose 110% in 4 years before the 1990 crash.*

The end screen is handled by the existing `ui/dashboard.py` `show_end()` in the terminal; the browser dashboard shows a static summary view.

---

## 6. Two Modes (student / expert)

Mode is passed as a CLI argument: `python main.py --mode student` (default) or `--mode expert`.

**Student mode** (this spec): macro-first, callouts visible, wealth chart prominent.

**Expert mode** (future spec): adds yield-per-property breakdown, leverage analysis, transaction cost impact, regional divergence charts. No callouts. The mode field in `turn_state.json` controls which panels the browser renders.

---

## 7. Files Changed

| File | Change |
|---|---|
| `kernel.py` | Era selection at init; read `UK_MACRO` each tick; write `turn_state.json`; start Flask thread |
| `state.py` | Add `start_year`, `start_half`, `era_label` to `SimulationState` |
| `shocks.py` | Replace scheduled shocks with `detect_events(prev, curr) → list[dict]` |
| `scenarios.py` | Remove drift/transition logic; keep `label_from_deltas(rate_delta, hpi_delta) → str` |
| `main.py` | Add `--mode` CLI argument |
| `visualisation/dashboard_server.py` | New — Flask server, background thread, `/state` endpoint |
| `static/dashboard.html` | New (at project root `static/`) — Chart.js dashboard, polls `/state` every 1.5s |
| `data/uk_macro_history.py` | No changes — already correct |

---

## 8. Out of Scope

- Expert mode charts (separate spec)
- Player interactive buy/sell decisions (existing stub unchanged)
- Mortgage/LTV mechanics in dashboard
- Regional divergence visualisation
- Mobile layout
