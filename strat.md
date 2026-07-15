# Actor Strategies

| | **You (Player)** | **Yield** | **Leverage** | **Capital** | **Value Add** | **BRRR** | **Demographic** | **Balanced** |
|---|---|---|---|---|---|---|---|---|
| **LTV** | 75% | 35% | 75% | 50% | 65% | 75% | 50% | 50% |
| **Min net yield to buy** | — | 5.0% | none | none | none | cash-flow positive | none | 3.5% |
| **Rate buy gate** | — | ≤ 7.0% | ≤ 6.5% | ≤ 6.5% | none | ≤ 7.0% | ≤ 6.5% | ≤ 6.0% |
| **Rate sell gate** | — | none | > 8.5% | none | none | > 10% (if cash-flow negative) | none | none |
| **Sell trigger** | — | — | Rate > 8.5% | 2 consecutive price falls | — | 3 ticks negative rent growth | — | — |
| **Property filter** | — | Highest net yield first | Any | ≥ £150k, highest value first | EPC D+ or value_add archetype, ≥ £120k | Distressed/HMO/short_let preferred | New region preferred | Any ≥ 3.5% net yield |
| **Refi** | — | No | No | No | Yes (≥ £20k headroom at 65%) | Yes (at 75%, recycled into next buy) | No | No |
| **EPC upgrade** | — | Yes (1.5×) | Yes (1.5×) | Yes (1.5×) | Yes — priority action (1.5×) | Yes — priority action (1.5×) | Yes (1.5×) | Yes (1.5×) |
| **Cash buffer** | — | 10% of deposit | 10% of deposit | 10% of deposit | 5% of deposit | 10% of deposit | 10% of deposit | 10% of deposit |

> All yields above are **net of the 12% management fee** (i.e. gross yield × 0.88).

## Decision Priority (all AI actors)

1. EPC upgrade (if owned property is band D or worse and cash covers 1.5× cost)
2. Refi (where applicable — Value Add, BRRR only)
3. Sell (if sell trigger conditions met)
4. Buy (if rate gate and affordability conditions met)
5. Hold

## Key Constants

| Constant | Value | Used by |
|---|---|---|
| `YIELD_TARGET` | 5.0% net | Yield |
| `YIELD_MAX_RATE` | 7.0% | Yield |
| `LEVERAGE_MAX_RATE_BUY` | 6.5% | Leverage |
| `LEVERAGE_SELL_RATE` | 8.5% | Leverage |
| `CAPITAL_MAX_RATE` | 6.5% | Capital |
| `CAPITAL_MIN_VALUE` | £150,000 | Capital |
| `CAPITAL_FALL_TICKS` | 2 | Capital |
| `VALUE_ADD_MIN_VALUE` | £120,000 | Value Add |
| `LTV_VALUE_ADD` | 65% | Value Add |
| `BRRR_RATE_GATE` | 7.0% | BRRR |
| `BRRR_SELL_RATE` | 10.0% | BRRR |
| `BRRR_RECYCLE_SIZE` | 4 properties | BRRR |
| `DEMO_MAX_RATE` | 6.5% | Demographic |
| `DEMO_SELL_RENT_TICKS` | 3 | Demographic |
| `MGMT_FEE_RATE` | 12% | All actors |
| `MORTGAGE_SPREAD` | 1.8% above BoE | All actors |

## Cash Flows by Action

All income figures are **quarterly** (3 months per tick).

### Buy
**Cash out:**
- Deposit = `price × (1 − LTV)`
- SDLT (stamp duty — additional property surcharge, see bands below)

**Mortgage rate:** fixed at `BoE + 1.8%` for 8 ticks (2 years), then variable at same spread.

**Void on purchase:** 0 ticks (btl/new_build), 1 tick (hmo/value_add/short_let).

### Hold (each tick, per property)
**Cash in:**
- Rent = `monthly_rent × 3 × (1 − 0.12)` (net of management fee, if not void)
- Savings interest on idle cash = `BoE × 0.75 / 4`

**Cash out:**
- Mortgage interest = `mortgage_balance × mortgage_rate / 4`

**Random events (probabilistic):**

| Archetype | Void chance/tick |
|---|---|
| btl | 8% |
| hmo | 3% |
| new_build | 4% |
| short_let | 12% |
| value_add | 10% |
| EPC D | +2% |
| EPC E | +4% |
| EPC F | +6% |
| EPC G | +8% |
| Falling rent market | +5% |

| Age | Maintenance chance/tick | Cost range |
|---|---|---|
| < 15 yrs | 3% | £300–£800 |
| 15–50 yrs | 8% | £500–£5,000 |
| 50–70 yrs | 13% | £1,000–£8,000 |
| 70+ yrs | 20% | £1,500–£12,000 |
| HMO (any age) | +5% | — |

### Sell
**Cash in:**
- `current_value − mortgage_balance − (current_value × 1.5%)` (agent fee)

### Refi
**Cash in:**
- Released equity = `(current_value × LTV) − existing_mortgage_balance`
- Minus flat fee = **£1,500**

Fixed term must have expired. Resets to a new 8-tick fixed term at current `BoE + 1.8%`.

### Upgrade (EPC)
**Cash out:**

| EPC Band | Cost |
|---|---|
| D (band 4) | £5,000 |
| E (band 5) | £8,000 |
| F (band 6) | £10,000 |
| G (band 7) | £10,000 |

**Effect:** EPC band improves by 2 bands. Rent increases by **10%**. Value increases by uplift factor:

| Original Band | Value uplift |
|---|---|
| D (band 4) | 6% |
| E (band 5) | 10% |
| F (band 6) | 15% |
| G (band 7) | 18% |

`base_value` is rebased to post-upgrade value so HPI appreciation compounds from the improved baseline.

### Renovate
**Cash out:** `current_value × 10%` (once per property)

**Effect:** rent +15%, property value +8%.

### Buy (Auction)
One auction property appears every 8 ticks at 15% below market value.

- Aggressive AI bids +5% over asking; Conservative AI bids at asking
- Player chooses bid premium: 0% / +5% / +10% / +15%
- Player wins if their bid ≥ highest AI bid (ties go to player)
- Player pays their own bid price

## SDLT Bands (additional-property surcharge throughout)

| Price range | Rate |
|---|---|
| £0–£125,000 | 3% |
| £125,001–£250,000 | 5% |
| £250,001–£925,000 | 8% |
| £925,001–£1,500,000 | 13% |
| Over £1,500,000 | 15% |

## EPC Purchase Discounts

| EPC Band | Purchase discount |
|---|---|
| D (band 4) | 5% |
| E (band 5) | 8% |
| F (band 6) | 12% |
| G (band 7) | 15% |

## Scoring

```
final_score = total_return − risk_cost
total_return = (net_portfolio_equity + cash) − initial_wealth
```

Risk deductions:
- **ICR stress:** portfolio fails ICR ≥ 1.25 at rate + 2% → capitalised shortfall × 2 years
- **LTV capital risk:** scales from 0% at LTV < 60% to 20% of portfolio value at LTV > 75%
- **Concentration risk:** > 60% in one region → up to 10% of portfolio value
- **EPC risk:** non-compliant properties haircut 15% of their value
