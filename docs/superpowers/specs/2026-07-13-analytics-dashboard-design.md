# Analytics Dashboard — Design Spec

**Date:** 2026-07-13
**Scope:** Add a per-actor analytics panel to `turn.html` showing 9 portfolio metrics for the player and all AI actors side-by-side.

---

## 1. Goal

Surface key investment metrics for all actors on the turn screen so the player can compare their portfolio health against AI opponents at a glance.

---

## 2. Metrics

| Row | Metric | Formula |
|---|---|---|
| 1 | GROSS YIELD | `(annual_rent / portfolio_value) * 100` % |
| 2 | UNREALISED | `sum(p.value - p.purchase_price)` across portfolio |
| 3 | ROE | `(annual_rent / (portfolio_value - total_debt)) * 100` % |
| 4 | COC RETURN | `(annual_rent / total_deposit_paid) * 100` %, where deposit = `purchase_price * 0.25` per property |
| 5 | AVG CAP GR | `mean((p.value - p.purchase_price) / p.purchase_price * 100)` across portfolio |
| 6 | REFI HEADRM | `(portfolio_value * 0.75) - total_debt` |
| 7 | EPC RISK | Count and total value of non-compliant properties; "None" if zero |
| 8 | REGION CONC | Highest single-region share of portfolio value, as % |
| 9 | CASH | Current cash balance |

`annual_rent` = `sum(p.rent * 12)` across portfolio for both player and AI.

---

## 3. Data Change: `purchase_price`

`purchase_price` must be stored on every property dict at acquisition time:

- **`init_game_state()`** — set `purchase_price = value` for all starting portfolio properties (player and each AI)
- **`apply_player_action()`** — when action is `'buy'`, set `prop['purchase_price'] = prop['value']` before appending to player portfolio
- **`ai_decide()`** — set `prop['purchase_price'] = prop['value']` when AI buys a property

---

## 4. New Function: `compute_analytics(gs)`

Add to `ui_web/app.py`. Returns a dict keyed by actor display name:

```python
{
    'You':           { 'gross_yield': 7.5, 'unrealised': -22000, 'roe': 7.5,
                       'coc_return': 8.0, 'avg_cap_gr': -5.0, 'refi_headrm': 456000,
                       'epc_count': 3, 'epc_value': 609000,
                       'region_conc': 43.5, 'cash': 585000 },
    'Mr Hugh Price': { ... },
    'Mr Max Lever':  { ... },
}
```

Handles empty portfolio gracefully (all metrics = 0 / None).

---

## 5. Layout

Full-width panel below the existing main content on `turn.html`. Single table, header row = actor names, 9 data rows.

```
┌─ ANALYTICS ──────────────────────────────────────────────────────┐
│              │      You        │  Mr Hugh Price  │  Mr Max Lever  │
│──────────────────────────────────────────────────────────────────│
│ GROSS YIELD  │     7.5%        │      5.4%       │     8.1%       │
│ UNREALISED   │   -£22k         │    +£64k        │    +£32k       │
│ ROE          │     7.5%        │      5.4%       │     8.1%       │
│ COC RETURN   │      8%         │      5.9%       │     9.3%       │
│ AVG CAP GR   │     -5%         │    +12.5%       │    -15%        │
│ REFI HEADRM  │    £456k        │     £431k       │    £134k       │
│ EPC RISK     │  3 · £609k      │     None        │  2 · £179k     │
│ REGION CONC  │    43.5%        │     52.1%       │    57.1%       │
│ CASH         │    £585k        │     £973k       │   £1,344k      │
└──────────────────────────────────────────────────────────────────┘
```

Actor name colours: You = `#00FF88`, Mr Hugh Price = `#FBBF24`, Mr Max Lever = `#F87171`.

---

## 6. Colour Logic

| Metric | Positive/good | Negative/bad | Neutral |
|---|---|---|---|
| UNREALISED | green (`#00FF88`) | red (`#F87171`) | — |
| AVG CAP GR | green | red | — |
| EPC RISK | green ("None") | red (any count) | — |
| GROSS YIELD, ROE, COC RETURN | green | — | — |
| REFI HEADRM, REGION CONC, CASH | — | — | white |

---

## 7. Files Changed

| File | Change |
|---|---|
| `ui_web/app.py` | Add `purchase_price` at buy points; add `compute_analytics(gs)`; pass `analytics` to `/turn` render |
| `ui_web/templates/turn.html` | Add analytics panel at bottom of main content column |

No new files required.

---

## 8. Out of Scope

- Sorting or filtering by metric
- Historical sparklines per metric
- Clicking a metric for drill-down
- Mobile layout changes
