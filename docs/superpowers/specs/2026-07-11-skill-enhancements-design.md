# Skill Enhancements — Design Spec

**Date:** 2026-07-11
**Project:** prof_game
**Status:** Approved

---

## Overview

Eight mechanics that add meaningful skill to the property investment game, phased across three releases. The core principle: every addition should create a decision the player must think about, not just observe.

---

## Phasing

| Phase | Features | Theme |
|---|---|---|
| 1 | Quarterly turns, Regional price variation | Structural foundation |
| 2 | Fixed/variable rate, Refinancing, Void risk | Financial mechanics |
| 3 | Value-add, Auction properties, Concentration penalty | Advanced tactics |

---

## Phase 1 — Structural Foundation

### 1.1 Quarterly Turns

**Change:** Each turn represents 3 months (one quarter) instead of 6 months (one half-year).

**Data:** `data/uk_macro_history.py` currently holds 82 semi-annual entries (1983 H1 → 2024 H2). Expand to ~164 quarterly entries by linear interpolation between each consecutive pair of semi-annual values across all three fields: `price_index`, `rate`, `rent_growth`.

**Turn counts:**

| Mode | Old turns | New turns | Simulated years |
|---|---|---|---|
| Short | 20 | 40 | 10 |
| Long | 40 | 80 | 20 |

**Per-tick calculations (period multiplier halves):**

| Calculation | Old | New |
|---|---|---|
| Rent income | `monthly_rent × 6` | `monthly_rent × 3` |
| Mortgage cost | `loan × rate / 12 × 6` | `loan × rate / 12 × 3` |
| AI income approx | `portfolio_value × 0.05 / 2` | `portfolio_value × 0.05 / 4` |

**Era selection safe ranges** shift to maintain the same year spans:
- 40-turn game: start year 1983–2014 (unchanged)
- 80-turn game: start year 1983–2004 (unchanged)

**UI:** Turn counter and progress bar update to new counts ("Turn 12 of 40").

---

### 1.2 Regional Price Variation

**New file:** `data/uk_regional_hpi.py` — regional multipliers relative to the national index, one value per semi-annual period (interpolated to quarterly alongside main data).

**Regions:** North, South, East, West, Midlands, Scotland, Wales.

**Multiplier profiles** derived from real UK regional HPI divergence:

| Region | Boom behaviour | Correction behaviour |
|---|---|---|
| South (London/SE) | Up to 1.5× national | Converges or underperforms |
| North | 0.7–0.85× national | Stable, less volatile |
| Scotland | 0.75–0.90× national | Stable |
| Wales | 0.70–0.85× national | Stable |
| Midlands | 0.90–1.05× national | Tracks national |
| East | 0.95–1.10× national | Tracks national |
| West | 0.90–1.05× national | Tracks national |

**Property update formula** changes from:

```python
biannual_growth = (price_index_next - price_index_now) / price_index_now
value *= (1 + biannual_growth)
rent  *= (1 + biannual_growth * 0.5)
```

To:

```python
regional_multiplier = uk_regional_hpi[region][tick]
regional_growth = national_growth * regional_multiplier
value *= (1 + regional_growth)
rent  *= (1 + regional_growth * 0.5)
```

**UI:** A regional heatmap panel on the turn dashboard — one row per region showing this turn's growth vs national (e.g. "+2.1% vs +1.4% national"). Helps the player identify which regions are running hot.

---

## Phase 2 — Financial Mechanics

### 2.1 Fixed vs Variable Mortgage Rate

At purchase, the player chooses LTV and rate type. The decision screen financing options expand to:

| Option | LTV | Rate type | Rate |
|---|---|---|---|
| Cash | 0% | — | — |
| Variable 50% | 50% | Tracks BoE base each turn | Current base rate |
| Variable 75% | 75% | Tracks BoE base each turn | Current base rate |
| 2-year fix 50% | 50% | Locked for 8 turns | Base rate + 0.5% |
| 2-year fix 75% | 75% | Locked for 8 turns | Base rate + 0.5% |
| 5-year fix 50% | 50% | Locked for 20 turns | Base rate + 0.25% |
| 5-year fix 75% | 75% | Locked for 20 turns | Base rate + 0.25% |

**Property state** gains three new fields:
- `rate_type` — `"variable"`, `"fix_2yr"`, or `"fix_5yr"`
- `locked_rate` — the rate at time of purchase (or refinance)
- `fix_turns_remaining` — decrements each turn; 0 means reverted to variable

When a fix expires, a news item is generated: *"Your 2-year fix on P-042 has expired — now on variable rate."*

---

### 2.2 Refinancing

**Mechanic:** Once every 5 turns, the player may refinance one mortgage from the decision screen. The cooldown is global (not per-property).

**Options shown on refinance:**
- Switch to current variable rate
- New 2-year fix at current base rate + 0.5%
- New 5-year fix at current base rate + 0.25%

**Portfolio table** shows a "FIX 8t" or "VAR" badge per property and a countdown of turns remaining on any fix. When refinance is available, a "Refinance available" indicator appears on the decision screen.

---

### 2.3 Void Risk

Each quarter, every owned property has a chance of going vacant. Probability formula:

```python
void_chance = max(0.0, (gross_yield - 3.0) / 100.0)
```

Examples:
- 3% yield → 0% void chance
- 6% yield → 3% void chance per quarter
- 10% yield → 7% void chance per quarter

When vacant, the property earns zero rent that turn. It automatically re-lets the following turn. No player action required.

**UI:** Vacant properties show a "VACANT" badge in the portfolio table and £0 rent for that turn. The news panel logs the event: *"P-017 went vacant this quarter — no rent collected."*

---

## Phase 3 — Advanced Tactics

### 3.1 Value-Add / Renovation

From the decision screen, the player may select "Renovate" on any owned property as their action for the turn (mutually exclusive with buy/sell).

**Cost:** 10% of the property's current market value, deducted from cash immediately.

**Effect (permanent):**
- Rent: +15%
- Property value: +8%

**Constraints:**
- Each property can only be renovated once (flagged in portfolio table as "RENOVATED")
- Player must have sufficient cash — no leveraging renovations
- Counts as the player's full action for that turn

**Economics:** At a 6% yield, the renovation cost net of the value uplift is ~2% of property value (0.10 - 0.08). The rent boost recovers this in ~2.2 years (9 quarters), making renovation a medium-term bet suited to stable-rate environments with a reasonable holding horizon.

---

### 3.2 Auction Properties

**Frequency:** One auction property appears every 8 turns.

**Pricing:** 15% below the regional market value for a comparable property.

**Bidding process (on the decision screen):**
1. Player enters a free bid amount (or passes)
2. Conservative AI bids at asking price (0% premium)
3. Aggressive AI bids at asking price + 5%
4. Highest bid wins; ties go to the player
5. Winner pays their bid and selects LTV/rate type as normal
6. If an AI wins, its aggregate portfolio value increases by the property's market value (consistent with existing AI mechanic — AI holds aggregate values, not named properties)

**Visibility:** Auction property is flagged with an "AUCTION" badge in the market table and disappears after one turn whether sold or not.

---

### 3.3 Regional Concentration Penalty

Added to the scoring formula alongside the existing leverage penalty.

**Trigger:** Player owns 4 or more properties in a single region.

**Formula:**

```python
for region in regions:
    count = properties_in_region(region)
    if count >= 4:
        excess = count - 3
        avg_value = total_regional_value / count
        concentration_penalty += excess * avg_value * 0.05
```

**Score formula becomes:**

```
score = portfolio_value + cash - leverage_penalty - concentration_penalty
```

**UI:** Concentration penalty shown as a separate line item in the score breakdown sidebar, alongside leverage penalty.

---

## Data Model Changes Summary

| Field | Added to | Phase |
|---|---|---|
| `quarterly_entries[]` | `uk_macro_history.py` | 1 |
| `uk_regional_hpi.py` | new file | 1 |
| `property.rate_type` | property object | 2 |
| `property.locked_rate` | property object | 2 |
| `property.fix_turns_remaining` | property object | 2 |
| `property.renovated` | property object | 3 |
| `game_state.refinance_cooldown` | game state | 2 |

---

## Out of Scope

- BRRR mechanic (recycle equity via refinance at new valuation) — deferred
- HMO / short-let property types — deferred
- Multi-player — deferred
- Vacancy duration beyond 1 turn — deferred
