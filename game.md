# RealEstGame — Specification (as built)

> This document describes the game as it actually runs today (`ui_web/app.py` + templates).
> Last updated: 2026-06-30.

---

## 1. Overview

RealEstGame is a turn-based property investment simulation. The player and two AI actors compete to build the most valuable portfolio across a randomly selected slice of real UK macroeconomic history. The era is hidden during play and revealed only at game end.

Each turn represents 6 months of simulated time. Macro conditions — house price growth, interest rates, rental growth — are driven by approximate historical UK data from 1983 to 2024.

---

## 2. Time Structure

### 2.1 Game Modes
Two modes selectable at the opening screen:

| Mode | Turns | Simulated years |
|---|---|---|
| Short | 20 | 10 years |
| Long | 40 | 20 years |

### 2.2 Turn Execution Order

Each turn runs in this sequence:

1. **Player decision** — buy, sell, or hold (with optional LTV choice)
2. **AI decisions** — both AI actors decide simultaneously
3. **Tick advance** — rent income paid, mortgage costs deducted, prices updated from historical data
4. **Market replenishment** — 2 new properties added each turn
5. **Leaderboard update** — scores recomputed for all actors
6. **Round summary** — decisions and outcomes displayed before next turn

---

## 3. Macro System

### 3.1 Historical Data Source

Macro values are drawn from `data/uk_macro_history.py` — a semi-annual dataset covering 1983 H1 → 2024 H2 (82 entries). Each entry contains:

| Field | Description |
|---|---|
| `price_index` | Nationwide/Halifax-based house price index (100 = 1983 H1) |
| `rate` | Bank of England base rate (%) |
| `rent_growth` | Estimated annualised private rental growth (%) |

Values are **approximate / illustrative** — derived from training knowledge of major trends. Authoritative sources are documented in `data/uk_macro_history.py`.

### 3.2 Hidden Era Mechanic

At game start, a random start year is selected from a safe range:
- 20-turn game: 1983–2014
- 40-turn game: 1983–2004

The start year is hidden from the player throughout. On the end screen it is revealed along with a named era label (e.g. *"Long Boom & The Run-Up to the GFC"*) and the selection range so the player can judge their luck.

### 3.3 Macro Display

The UI shows three macro values each turn with trend arrows:
- **Price Index** — normalised so game always opens at 100.0
- **Interest Rate** — BoE base rate %
- **Rent Growth** — annual % estimate

SVG sparklines show the history of each metric as the game progresses.

### 3.4 Scenario Labels

A scenario label (Baseline / Boom / Recovery / Correction / Crash / High Rates) is derived each tick from the observed data:

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

At game start the market contains 10 properties. 2 new listings are added each turn, priced relative to the current price index. Properties have:
- `id` — unique identifier (P-xxx)
- `region` — one of: North, South, East, West, Midlands, Scotland, Wales
- `value` — current market value in £
- `rent` — monthly rent in £

### 4.2 Valuation Update (per tick)

Property values and rents move in line with the historical price growth for that period:

```
biannual_growth = (price_index_next - price_index_now) / price_index_now
value *= (1 + biannual_growth)
rent  *= (1 + biannual_growth * 0.5)   # rents lag prices
```

### 4.3 Gross Yield

```
gross_yield = (rent * 12) / value * 100   # annual %
```

---

## 5. Actor Model

### 5.1 Starting Positions

All three actors start with equal total wealth (£1,200,000):

| Actor | Cash | Portfolio Value | Properties |
|---|---|---|---|
| You | £345,000 | £855,000 | 5 |
| Conservative | £360,000 | £840,000 | 5 |
| Aggressive | £190,000 | £1,010,000 | 5 |

### 5.2 Income Per Tick

Each turn actors receive 6 months of rent income:

```
rent_income = sum(monthly_rent) * 6
```

AI actors also receive a flat 5% annualised yield on portfolio value (approximation):

```
ai_income = portfolio_value * 0.05 / 2
```

Mortgage interest is deducted (see §6.3).

---

## 6. Player Actions

### 6.1 Hold
No transaction. Rent income still collected.

### 6.2 Buy

Player selects a property from the market and a financing option:

| Option | LTV | Deposit required | Monthly cost |
|---|---|---|---|
| Cash | 0% | Full value | £0 |
| Mortgage | 50% | 50% of value | `loan × rate / 12` |
| High leverage | 75% | 25% of value | `loan × rate / 12` |

Monthly mortgage payment is interest-only at the current BoE base rate.

### 6.3 Sell

Player selects a property from their portfolio. Net proceeds:

```
net_proceeds = max(0, property_value - outstanding_loan)
```

The mortgage (if any) is repaid from proceeds. The property returns to the market.

### 6.4 Forced Sale

If player cash falls below −£50,000, the cheapest portfolio property is automatically sold to cover the shortfall.

---

## 7. AI Actors

### 7.1 Conservative

- **Buy trigger**: gross yield > 4%, can afford 50% deposit
- **Buy preference**: cheapest qualifying property (lower risk)
- **Sell trigger**: price index falling turn-on-turn (exits early)
- **LTV**: 50%

### 7.2 Aggressive

- **Buy trigger**: can afford 25% deposit on any market property
- **Buy preference**: highest-value affordable property
- **Sell trigger**: Correction or Crash scenario label (exits late)
- **LTV**: 75%

### 7.3 AI Sell Mechanics

When an AI sells, it liquidates one average-value position:

```
prop_value = portfolio_value / props
net_proceeds = prop_value - (total_debt / props)
```

The sold property is added to the market. Debt is reduced proportionally.

---

## 8. Scoring

### 8.1 Score Formula

```
score = portfolio_value + cash - leverage_penalty
```

### 8.2 Leverage Penalty

Debt exceeding 50% LTV incurs a 10% penalty on the excess:

```
safe_debt      = portfolio_value * 0.5
excess_debt    = max(0, total_debt - safe_debt)
leverage_penalty = excess_debt * 0.10
```

### 8.3 Leaderboard

All three actors are ranked by score at the end of every turn. The player's rank and score are shown in the sidebar throughout.

---

## 9. UI / Screens

The web UI runs as a Flask app (`ui_web/app.py`, port 5050).

| Route | Screen | Purpose |
|---|---|---|
| `/` | Opening | Starting positions, market preview, mode selection |
| `/start` (POST) | — | Initialises game state, redirects to Turn |
| `/turn` | Turn dashboard | Macro sidebar, portfolio, AI positions, news, actor chart |
| `/decision` | Decision | Market table, portfolio, buy/sell/hold form with LTV selector |
| `/decision/confirm` (POST) | — | Applies all actions, advances tick, redirects to Summary |
| `/round-summary` | Round Summary | Player and AI decisions for the completed turn |
| `/end` | End screen | Final scores, breakdown, era reveal |
| `/play-again` (POST) | — | Resets state, redirects to Opening |

### 9.1 Turn Dashboard Panels

- **Sidebar**: tick progress bar, macro values with trend arrows and SVG sparklines, rank and score
- **Actor Positions**: stacked proportional bar chart — all turns shown as fixed-width columns from the start
- **Your Portfolio**: property table with values, rent, yield; mortgage table if leveraged
- **AI Positions**: last action (BUY / SELL / HOLD badge) and rationale for each AI
- **News**: last 2 events (scenario shifts, forced sales, market notes)

### 9.2 End Screen

- Leaderboard ranking
- Player breakdown: portfolio value, cash, estimated rent
- Final score
- **Era Reveal**: the real UK period played through, named era label, and the random selection range

---

## 10. Architecture

```
RealEstGame/
├── data/
│   └── uk_macro_history.py     # semi-annual UK macro data 1983-2024
├── ui_web/
│   ├── app.py                  # Flask app — all game logic
│   └── templates/
│       ├── base.html
│       ├── opening.html
│       ├── turn.html
│       ├── decision.html
│       ├── round_summary.html
│       └── end.html
└── ui_kivy/
    └── dummy_data.py           # starting positions (shared by both UIs)
```

To run:
```bash
cd ui_web
python app.py
# Open http://localhost:5050
```

---

## 11. Known Limitations / Future Work

- Single-player only (module-level `GAME_STATE` — one session at a time)
- AI portfolio is an aggregate value, not individual named properties
- Rental growth in `uk_macro_history.py` is estimated pre-2011; ONS IPHRP data only available from 2011
- Mortgage rate is fixed at the BoE base rate at time of purchase (no refinancing)
- No vacancy modelling, maintenance costs, or tenant events
- No regional price variation (all properties move with the national index)
- Scenario labels are derived heuristically; they do not map to exact historical events
