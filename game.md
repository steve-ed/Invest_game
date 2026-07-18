# RealEstGame — Specification (as built)

> Last updated: 2026-07-18. Describes the `kernel.py` architecture.

---

## 1. Overview

RealEstGame is a turn-based property investment simulation. The player and two AI actors (drawn randomly from six available strategies) compete to build the strongest risk-adjusted portfolio across a randomly selected slice of real UK macroeconomic history. The era is hidden during play and revealed only at game end.

Each turn represents **6 months** of simulated time (semi-annual). Macro conditions — house price growth, interest rates, rental growth — are driven by approximate historical UK data from 1983 to 2024.

---

## 2. Time Structure

### 2.1 Game Modes

| Mode | Turns | Simulated years |
|---|---|---|
| Short | 20 | 10 years |
| Long | 40 | 20 years |

### 2.2 Turn Execution Order

Each turn runs in this sequence:

1. **Player decision** — buy, sell, hold, upgrade, refi, renovate (with optional LTV choice)
2. **AI decisions** — all AI actors decide simultaneously; brrr and value_add strategies also bid at auction listings
3. **Tick advance** — rent income paid, mortgage costs deducted, prices updated
4. **Random events** — void periods, maintenance costs, branching narrative events
5. **EPC mandate check** — at a random tick between 5 and 8, non-compliant properties enter a 4-tick grace window
6. **Market replenishment** — properties added to keep minimum available
7. **Auction scheduling** — one auction property added every 8 ticks
8. **Leaderboard update** — scores recomputed for all actors

---

## 3. Macro System

### 3.1 Historical Data Source

Macro values are drawn from `data/uk_macro_history.py` — a semi-annual dataset covering 1983 H1 → 2024 H2. Each entry contains:

| Field | Description |
|---|---|
| `price_index` | Nationwide/Halifax-based house price index (100 = game start) |
| `interest_rate` | Bank of England base rate (decimal, e.g. 0.05 = 5%) |
| `rent_growth` | Estimated annualised private rental growth (decimal) |

### 3.2 Hidden Era Mechanic

At game start, a random start year is selected. The start year is hidden from the player throughout. On the end screen it is revealed with a named era label (e.g. *"Long Boom & The Run-Up to the GFC"*).

### 3.3 Scenario Labels

Derived each tick from observed data:

| Condition | Label |
|---|---|
| Price growth > 2% per half-year | Boom |
| Price fall > 1.5%, rate > 3% | Correction |
| Price fall > 1.5%, rate ≤ 3% | Crash |
| Rate > 8% | High Rates |
| Price growth 0.5–2% | Recovery |
| Otherwise | Baseline |

---

## 4. Property Model

### 4.1 Market

At game start the market contains 19 named properties (p01–p15, m1–m4). Properties replenish dynamically from 8 regional profiles to maintain a minimum of 4 available listings.

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `region` | One of: London, South, East, West, Midlands, North, Scotland, Wales |
| `archetype` | btl \| hmo \| short_let \| new_build \| value_add |
| `current_value` | Current market value in £ |
| `rent` | Monthly rent in £ |
| `epc_band` | 1=A (best) … 7=G (worst) |
| `age` | Property age in years |
| `mortgage_balance` | Outstanding mortgage debt |
| `renovated` | Whether property has been renovated (once per property) |
| `is_auction` | Whether property is an auction listing |

### 4.2 Regional Pricing

Properties are priced relative to a national base of £165,000 multiplied by regional price level:

| Region | Price level | Annual yield | HPI factor |
|---|---|---|---|
| London | 2.50× | 3.5% | 1.35 |
| South | 1.50× | 4.0% | 1.15 |
| East | 1.20× | 4.5% | 1.10 |
| West | 1.00× | 4.8% | 0.95 |
| Midlands | 0.85× | 5.5% | 0.90 |
| North | 0.75× | 6.0% | 0.85 |
| Scotland | 0.80× | 5.5% | 0.88 |
| Wales | 0.70× | 6.5% | 0.80 |

### 4.3 EPC Purchase Discounts

Poor EPC properties are priced below their HPI-adjusted value to reflect compliance risk:

| EPC Band | Purchase discount |
|---|---|
| D (band 4) | 5% |
| E (band 5) | 8% |
| F (band 6) | 12% |
| G (band 7) | 15% |

### 4.4 Valuation Update (per tick)

Property values move with regional HPI:

```
semi_annual_growth = (price_index_next - price_index_now) / price_index_now * hpi_factor
current_value      *= (1 + semi_annual_growth)
rent               *= (1 + semi_annual_growth * 0.5)   # rents lag prices
```

---

## 5. Actor Model

### 5.1 Starting Positions

All actors start with approximately equal total wealth (~£1,500,000). The player gets 3 randomly assigned properties from the starting market; two AI actors each get 2 properties from distinct strategy profiles.

### 5.2 Income Per Tick (semi-annual)

**Cash in:**
- Rent income = `monthly_rent × 6 × (1 − 0.12)` (12% management fee deducted)
- Savings interest on cash = `BoE_rate × 0.75 / 2` (competitive savings rate, semi-annual)

**Cash out:**
- Mortgage interest = `mortgage_balance × mortgage_rate / 2`

---

## 6. Player Actions

### 6.1 Hold
No transaction. Rent income still collected.

### 6.2 Buy

Player selects a property from the market and an LTV:

| Option | LTV | Deposit required |
|---|---|---|
| Cash | 0% | Full value |
| Mortgage | 50% | 50% of value |
| High leverage | 75% | 25% of value |

Mortgage rate = `BoE rate + 1.8%`, fixed for 4 ticks (2 years), then variable.

**SDLT (additional-property surcharge):**

| Price range | Rate |
|---|---|
| £0–£125,000 | 3% |
| £125,001–£250,000 | 5% |
| £250,001–£925,000 | 8% |
| £925,001–£1,500,000 | 13% |
| Over £1,500,000 | 15% |

### 6.3 Sell

Net proceeds = `current_value − mortgage_balance − (current_value × 1.5%)` (agent fee)

### 6.4 Upgrade (EPC)

**Cost by band:**

| EPC Band | Cost |
|---|---|
| D (band 4) | £5,000 |
| E (band 5) | £8,000 |
| F (band 6) | £10,000 |
| G (band 7) | £10,000 |

**Effect:** EPC band improves by 2 bands. Rent increases by **10%**. Property value increases by the EPC uplift factor:

| Original EPC Band | Value uplift |
|---|---|
| D (band 4) | 6% |
| E (band 5) | 10% |
| F (band 6) | 15% |
| G (band 7) | 18% |

`base_value` is rebased to post-upgrade value so future HPI appreciation compounds from the improved baseline.

### 6.5 Refi (Remortgage)

Available when the fixed-rate term has expired and there is headroom at the target LTV.

- Released equity = `(current_value × LTV) − existing_mortgage_balance`
- Flat fee = **£1,500**
- Resets to a new 4-tick fixed term at current `BoE + 1.8%`

### 6.6 Renovate

Pay 10% of current property value to improve an owned property. Can only be done once per property.

- **Cost:** `current_value × 10%`
- **Effect:** rent +15%, property value +8%

### 6.7 Buy (Auction)

Auction properties appear every 8 ticks, priced 15% below market value, flagged with an AUCTION badge.

- Player selects a bid premium: Asking / +5% / +10% / +15%
- Aggressive AI always bids +5%; Conservative AI bids at asking
- Player wins if their bid ≥ highest AI bid (ties go to player)
- Player pays their bid price (not asking price)
- The **brrr** and **value_add** AI strategies also participate in auctions, bidding at asking price when cash reserves allow

### 6.8 Forced Sale

If player cash goes negative, the cheapest portfolio property is automatically sold to cover the shortfall.

### 6.9 Auto-Remortgage

When a fixed-rate term expires (after 4 ticks) and the actor does not proactively refi, the system automatically remortgages the property:

- **Arrangement fee:** 1% of outstanding mortgage balance (deducted from cash)
- **New rate:** current `BoE + 1.8%` at time of auto-remortgage
- **New fixed term:** 4 ticks (2 years)

This preserves one full tick as a window for the actor to refi voluntarily before the auto-remortgage fires.

---

## 7. EPC Mandate

At a random tick between tick 5 and tick 8, a government mandate fires requiring all properties to be EPC C (band 3) or better within 4 ticks. Non-compliant properties (EPC D–G):

1. Enter an EPC void — no rent income until upgraded to EPC C or better
2. If still non-compliant after the 4-tick grace window, force-sold at **85% of current value** minus 1.5% agent fee minus mortgage balance

---

## 8. Random Events (per tick, per property)

### 8.1 Void Risk

| Condition | Extra void chance |
|---|---|
| btl archetype | 8% base |
| hmo archetype | 3% base |
| new_build archetype | 4% base |
| short_let archetype | 12% base |
| value_add archetype | 10% base |
| EPC D | +2% |
| EPC E | +4% |
| EPC F | +6% |
| EPC G | +8% |
| Falling rent market | +5% |

### 8.2 Maintenance Risk

| Property age | Maintenance chance/tick | Cost range |
|---|---|---|
| < 15 years | 3% | £300–£800 |
| 15–50 years | 8% | £500–£5,000 |
| 50–70 years | 13% | £1,000–£8,000 |
| 70+ years | 20% | £1,500–£12,000 |
| HMO (any age) | +5% | — |

---

## 9. Scoring

### 9.1 Score Formula

```
final_score = total_return − risk_cost

total_return = (portfolio_equity + cash) − initial_wealth
portfolio_equity = sum(current_value − mortgage_balance) for each owned property
```

### 9.2 Risk Costs (deducted from score)

**ICR stress test:** If the portfolio fails ICR ≥ 1.25 at current rate + 2%, the shortfall is capitalised over 2 years:
```
icr_cost = (stressed_annual_interest × 1.25 − annual_rent) × 2
```

**LTV capital risk:** Potential loss in a 20% price correction scales with LTV above 60%:
- LTV 60–75%: up to 5% of portfolio value
- LTV > 75%: up to 20% of portfolio value (scales to max at LTV 100%)

**Concentration risk:** If any single region exceeds 60% of portfolio value, penalty scales to 10% of portfolio value.

**EPC regulatory risk:** Non-compliant properties (EPC D–G) are haircut by 15% of their value.

---

## 10. AI Strategies

Six AI strategies are available. Two are randomly selected each game.

| Actor Name | Strategy | Summary |
|---|---|---|
| Ms Di Vidend | yield | Buys for income at low LTV; yield-first filter |
| Mr Hugh Price | capital | Buys high-value properties for appreciation |
| Mr Ray Novate | value_add | Targets distressed EPC stock; upgrades then refis |
| Mr Reid Furbish | brrr | Buy, Refurbish, Refinance, Repeat cycle |
| Mr Max Lever | leverage | High LTV, rate-sensitive; sells on rate spikes |
| Ms Demi Graphic | demographic | Diversifies regions; exits on sustained rent decline |

See `strat.md` for full strategy parameters.

---

## 11. Architecture

```
realestgame-v2/
├── kernel.py                   # SimulationKernel — main game loop
├── state.py                    # SimulationState, Property, ActorState, MacroState
├── actors.py                   # ActorManager — rent, mortgage, savings per tick
├── ai.py                       # AIController — all 6 AI strategy implementations
├── scoring.py                  # ScoringEngine — risk-adjusted score
├── property_model.py           # HPI-based valuation updates
├── void_maintenance.py         # VoidMaintenanceEngine — random void/maintenance events
├── player/choices.py           # PlayerChoiceEngine — reads actions from GameBus or stdin
├── game_bus.py                 # GameBus — IPC between kernel thread and Flask server
├── visualisation/
│   ├── dashboard_server.py     # Flask server serving turn_state.json
│   └── turn_state.json         # Written each tick; read by dashboard.html
├── static/dashboard.html       # Single-file web dashboard (player UI)
├── data/uk_macro_history.py    # Quarterly UK macro data 1983–2024
└── game_on.py                  # 99-game benchmark runner
```

To run:
```bash
python main.py
# Open http://localhost:5050
```
