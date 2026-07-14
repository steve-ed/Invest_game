# Actor Strategies

| | **You (Player)** | **Yield** | **Leverage** | **Capital** | **Value Add** | **BRRR** | **Demographic** | **Balanced** |
|---|---|---|---|---|---|---|---|---|
| **LTV** | 75% | 35% | 75% | 50% | 65% | 75% | 50% | 50% |
| **Min yield to buy** | 5.5% | 6.0% | none | none | none | none | none | 4.0% |
| **Rate buy gate** | ≤ 6.5% | ≤ 7.0% | ≤ 6.5% | ≤ 6.5% | none | ≤ 7.0% | ≤ 6.5% | ≤ 6.0% |
| **Rate sell gate** | > 6.5% (if LTV > 80%) | none | > 8.5% | none | none | > 10% (if cash-flow negative) | none | none |
| **Sell trigger** | High LTV + rate spike | — | Rate > 8.5% | 2 consecutive price falls | — | 3 ticks negative rent growth | — | — |
| **Property filter** | Highest yield first | Highest yield first | Any | ≥ £150k, highest value first | EPC D+ or value_add archetype, ≥ £120k | Distressed/HMO/short_let preferred | New region preferred | Any ≥ 4% yield |
| **Refi** | Yes (≥ £20k headroom at 75%) | No | No | No | Yes (at 65% after upgrade) | Yes (at 75%, recycled into next buy) | No | No |
| **EPC upgrade** | Yes (2× cost reserve) | Yes (1.5×) | Yes (1.5×) | Yes (1.5×) | Yes — priority action (1.5×) | Yes — priority action (1.5×) | Yes (1.5×) | Yes (1.5×) |
| **Cash buffer** | £150k fixed reserve | 10% of deposit | 10% of deposit | 10% of deposit | 5% of deposit | 10% of deposit | 10% of deposit | 10% of deposit |

## Decision Priority (all actors)

1. EPC upgrade (if owned property is band D or worse and cash covers 1.5× cost)
2. Refi (where applicable — Player, Value Add, BRRR only)
3. Sell (if sell trigger conditions met)
4. Buy (if rate gate and affordability conditions met)
5. Hold

## Key Constants

| Constant | Value | Used by |
|---|---|---|
| `YIELD_TARGET` | 6.0% | Yield |
| `YIELD_MAX_RATE` | 7.0% | Yield |
| `LEVERAGE_MAX_RATE_BUY` | 6.5% | Leverage |
| `LEVERAGE_SELL_RATE` | 8.5% | Leverage |
| `CAPITAL_MAX_RATE` | 6.5% | Capital |
| `CAPITAL_MIN_VALUE` | £150,000 | Capital |
| `CAPITAL_FALL_TICKS` | 2 | Capital |
| `VALUE_ADD_MIN_VALUE` | £120,000 | Value Add |
| `BRRR_RATE_GATE` | 7.0% | BRRR |
| `BRRR_SELL_RATE` | 10.0% | BRRR |
| `BRRR_RECYCLE_SIZE` | 4 properties | BRRR |
| `DEMO_MAX_RATE` | 6.5% | Demographic |
| `DEMO_SELL_RENT_TICKS` | 3 | Demographic |
| `HIGH_RATE_THRESHOLD` | 6.5% | Player |
| `BUY_CASH_RESERVE` | £150,000 | Player |

## Cash Flows by Action

### Buy
**Cash out:**
- Deposit = `price × (1 − LTV)`
- SDLT (stamp duty — see bands below)

**Mortgage rate:** fixed at `BoE + 1.8%` for 4 ticks, then variable at same spread.

**Void on purchase:** 0 ticks (btl/new_build), 1 tick (hmo/value_add/short_let).

### Hold (each tick, per property)
**Cash in:**
- Rent = `monthly_rent × 6` (if not void)
- Savings interest on idle cash = `BoE × 0.75 / 2`

**Cash out:**
- Mortgage interest = `mortgage_balance × mortgage_rate / 2`

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
- `current_value − mortgage_balance − agent_fee`
- Agent fee = `current_value × 1.5%`

No CGT applied.

### Refi
**Cash in:**
- Released equity = `(current_value × LTV) − existing_mortgage_balance`
- Minus fee = `new_mortgage_balance × 1%`

Fixed term must have expired. Resets to a new 4-tick fixed term at current `BoE + 1.8%`.

### Upgrade (EPC)
**Cash out:**

| EPC Band | Cost |
|---|---|
| D (band 4) | £5,000 |
| E (band 5) | £8,000 |
| F (band 6) | £10,000 |
| G (band 7) | £10,000 |

**Effect:** EPC band improves by 2 bands. Rent increases by **5%**.

### EPC Force-Sell (mandate at tick 10)
If non-compliant (EPC D–G) and not upgraded within 2 ticks: force-sold at **85% of current value**, minus 1.5% agent fee, minus mortgage balance.

## SDLT Bands (additional-property surcharge throughout)

| Price range | Rate |
|---|---|
| £0–£125,000 | 3% |
| £125,001–£250,000 | 5% |
| £250,001–£925,000 | 8% |
| £925,001–£1,500,000 | 13% |
| Over £1,500,000 | 15% |
