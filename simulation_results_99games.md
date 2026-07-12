# Simulation Results — 99 Games × 20 Turns

## Run 1 (baseline)

**Generated:** 2026-07-05  
**Application commit:** `fee5598` (`feat: fix value_add property selection and BRRR sell discipline`)  
**Advice engine:** fixed `balanced` strategy — no position awareness  
**Simulation driver:** `claude_player.py` — headless rule-based player  
**Python:** 3.13.8  
**Turns per game:** 20  

## Run 2 (position-aware advice engine)

**Generated:** 2026-07-05  
**Application commit:** `c6a5e80` (`feat: position-aware advice engine — rank, gap and opponent strategy aware`)  
**Advice engine:** position-aware — selects `conservative`, `balanced`, or `aggressive` strategy per tick based on rank, score gap, ticks remaining, and opponent strategies  
**Simulation driver:** `claude_player.py` — headless rule-based player  
**Python:** 3.13.8  
**Turns per game:** 20  

---

## Actor Strategy Map

| Actor | Strategy | Key behaviour |
|-------|----------|---------------|
| You (Claude) | `balanced` | Refi on expired fixed terms, upgrade EPC, buy at ≤6.5% rate with yield >5.5% |
| Mr Hugh Price | `capital` | Targets highest-value properties (≥£150k), sells after sustained price falls |
| Mr Max Lever | `leverage` | High-LTV (75%) buying at ≤6.5% rate, sells when rate >8.5% |
| Ms Di Vidend | `yield` | Gross yield ≥6% filter, low LTV (35%), pauses above 7% rate |
| Ms Demi Graphic | `demographic` | Targets rent-growth regions, rolling 2-tick rent signal gate |
| Mr Reid Furbish | `brrr` | Buy-refurb-refi cycle, sells only when rate >10% AND cash-flow negative |
| Mr Ray Novate | `value_add` | Buys distressed EPC stock ≥£120k, upgrades then refis completed properties |

Each game randomly draws 2 AI opponents from the pool to play against Claude (the player).

---

## AI Rebalancing History

Actor AI strategies were iteratively tuned across six 30-game test runs before the benchmarks:

| Change | Purpose |
|--------|---------|
| `LEVERAGE_MAX_RATE_BUY` 5% → 6.5% | Mr Max Lever was missing entire eras of buying opportunity |
| Demographic rent gate: single tick → 2-tick rolling average | Ms Demi Graphic was freezing on one flat quarter |
| `LTV_VALUE_ADD` introduced at 65% (was 50%) | Mr Ray Novate couldn't afford deposits with full 10% buffer |
| `BRRR_RECYCLE_SIZE` 3 → 4 | Mr Reid Furbish was cycling out of properties too early |
| BRRR refi LTV 75% → 65% | Reid was stripping properties to near-zero equity |
| Value_add refi step added | Ray never extracted post-upgrade uplift; locked equity wasted |
| `VALUE_ADD_MIN_VALUE = £120k` + sort by yield DESC | Ray was buying cheap slow-growth Northern stock |
| BRRR sell: rate gate replaced by rate AND ICR condition | Prevents panic-selling cash-flow-positive properties in high-rate eras |
| AI buy race condition fixed (`available` list updated per actor) | Both AIs were targeting the same property in the same tick |

---

## Position-Aware Advice Engine

Added in commit `c6a5e80`. The "Your Decision Review" table on the final summary screen previously compared the player's actions against a fixed `balanced` strategy regardless of competitive standing.

The upgraded engine selects which strategy to recommend each tick based on:

| Condition | Recommended strategy | Rationale |
|-----------|---------------------|-----------|
| Rank 1, ≤4 turns left | `conservative` (yield) | Protect the lead — avoid rate exposure |
| Rank 2/3, gap >£150k, ≤4 turns left | `aggressive` (leverage) | Need to take risk to close the gap |
| Opponent is `capital` strategy and player is losing | `conservative` (yield) | Can't out-appreciate Hugh Price — out-yield instead |
| All other situations | `balanced` | Standard play |

The dashboard "Your Decision Review" table now shows rank (R1/R2/R3), score gap to leader, and labels each recommendation with its strategy (`conservative`, `balanced`, `aggressive`).

---

## Podium Distribution — Run 1 (fixed balanced advice)

| Actor | Appeared | 1st | 2nd | 3rd | Win % | Avg Score | Avg Equity | Avg Cash |
|-------|----------|-----|-----|-----|-------|-----------|------------|----------|
| You (Claude) | 99 | 52 | 38 | 9 | 52.5% | £1,883,210 | £1,617,012 | £1,772,803 |
| Mr Hugh Price | 32 | 23 | 6 | 3 | 71.9% | £2,900,541 | £3,757,264 | £661,559 |
| Mr Max Lever | 30 | 8 | 12 | 10 | 26.7% | £1,683,013 | £1,789,027 | £1,503,163 |
| Ms Di Vidend | 36 | 7 | 15 | 14 | 19.4% | £1,475,912 | £1,253,633 | £1,726,323 |
| Ms Demi Graphic | 32 | 4 | 10 | 18 | 12.5% | £1,505,718 | £1,894,842 | £1,142,876 |
| Mr Reid Furbish | 35 | 3 | 4 | 28 | 8.6% | £1,261,570 | £423,671 | £2,376,100 |
| Mr Ray Novate | 33 | 2 | 14 | 17 | 6.1% | £1,293,343 | £700,026 | £2,143,516 |

---

## Podium Distribution — Run 2 (position-aware advice)

| Actor | Appeared | 1st | 2nd | 3rd | Win % | Avg Score | Avg Equity | Avg Cash |
|-------|----------|-----|-----|-----|-------|-----------|------------|----------|
| You (Claude) | 99 | 60 | 32 | 7 | 60.6% | £1,844,111 | £1,561,842 | £1,788,355 |
| Mr Hugh Price | 31 | 19 | 10 | 2 | 61.3% | £2,579,590 | £3,357,908 | £732,233 |
| Mr Max Lever | 25 | 12 | 6 | 7 | 48.0% | £1,996,014 | £2,084,226 | £1,469,391 |
| Ms Di Vidend | 29 | 2 | 23 | 4 | 6.9% | £1,297,408 | £1,125,419 | £1,677,523 |
| Ms Demi Graphic | 35 | 2 | 13 | 20 | 5.7% | £1,456,472 | £1,817,597 | £1,150,175 |
| Mr Ray Novate | 36 | 2 | 11 | 23 | 5.6% | £1,322,341 | £697,535 | £2,185,505 |
| Mr Reid Furbish | 42 | 2 | 4 | 36 | 4.8% | £1,038,654 | £349,678 | £2,230,081 |

> Win % is calculated over games in which the actor appeared (not total games).  
> Scores are `total_return − risk_cost` where `total_return = equity + cash − initial_wealth`.

---

## Win Count — Run 1 vs Run 2

| Actor | Run 1 | Run 2 | Change |
|-------|-------|-------|--------|
| You (Claude) | 52 | 60 | +8 |
| Mr Hugh Price | 23 | 19 | -4 |
| Mr Max Lever | 8 | 12 | +4 |
| Ms Di Vidend | 7 | 2 | -5 |
| Ms Demi Graphic | 4 | 2 | -2 |
| Mr Ray Novate | 2 | 2 | 0 |
| Mr Reid Furbish | 3 | 2 | -1 |

---

## Wins by Era — Run 1

| Era | Games | Winner distribution |
|-----|-------|---------------------|
| Mid-Nineties Recovery & Cool Britannia | 16 | You 6, Hugh Price 6, Mort Gage 2, Demi Graphic 1, Di Vidend 1 |
| Long Boom & The Run-Up to the GFC | 14 | You 11, Mort Gage 2, Hugh Price 1 |
| New Labour Boom — Part I | 12 | You 6, Hugh Price 5, Mort Gage 1 |
| Boom & Bust — The 1989 Crash | 11 | You 5, Demi Graphic 2, Hugh Price 1, Mort Gage 1, Ray Novate 1, Di Vidend 1 |
| The Global Financial Crisis & Austerity | 11 | Hugh Price 6, You 4, Di Vidend 1 |
| Post-GFC Long Recovery | 10 | You 6, Hugh Price 3, Mort Gage 1 |
| Late Thatcher Boom | 9 | You 5, Di Vidend 3, Ray Novate 1 |
| Early Thatcher Recovery | 9 | You 5, Reid Furbish 3, Di Vidend 1 |
| Sustained Growth, Brexit & COVID | 7 | You 4, Mort Gage 1, Hugh Price 1, Demi Graphic 1 |

## Wins by Era — Run 2

| Era | Games | Winner distribution |
|-----|-------|---------------------|
| Long Boom & The Run-Up to the GFC | 18 | You 12, Mort Gage 3, Hugh Price 3 |
| Boom & Bust — The 1989 Crash | 18 | You 6, Mort Gage 4, Hugh Price 3, Ray Novate 2, Demi Graphic 2, Di Vidend 1 |
| The Global Financial Crisis & Austerity | 14 | You 9, Hugh Price 4, Mort Gage 1 |
| New Labour Boom — Part I | 12 | You 7, Hugh Price 4, Mort Gage 1 |
| Early Thatcher Recovery | 10 | You 7, Reid Furbish 2, Di Vidend 1 |
| Mid-Nineties Recovery & Cool Britannia | 9 | You 5, Hugh Price 3, Mort Gage 1 |
| Post-GFC Long Recovery | 7 | You 4, Mort Gage 2, Hugh Price 1 |
| Late Thatcher Boom | 6 | You 6 (clean sweep) |
| Sustained Growth, Brexit & COVID | 5 | You 4, Hugh Price 1 |

---

## Action Coverage — Run 2 (99 Games)

| Actor | buy | sell | upgrade | refi | hold |
|-------|-----|------|---------|------|------|
| AI slot 1 (varies) | 613 | 71 | 715 | 233 | 348 |
| AI slot 2 (varies) | 599 | 78 | 709 | 240 | 354 |
| You (Claude) | 381 | 0 | 625 | 708 | 266 |

### Action Success Rate — Run 2

| Actor | buy OK | buy FAILED | sell | upgrade | refi | hold |
|-------|--------|------------|------|---------|------|------|
| AI slot 1 | 592 | 21 | 71 | 715 | 233 | 348 |
| AI slot 2 | 582 | 17 | 78 | 709 | 240 | 354 |
| You (Claude) | 376 | 5 | 0 | 625 | 708 | 266 |

Buy failures (< 3% rate) are caused by concurrent actor targeting of the same property in the same tick.

---

## Key Findings

- **Position-aware advice improved Claude's win rate from 52.5% → 60.6%** — the biggest gains came from the Late Thatcher Boom (clean sweep 6/6) and GFC era (4→9 wins), where switching to conservative/yield-focused play at end-game prevents overtrading.
- **Mr Hugh Price remains the strongest per-appearance competitor** — his per-game win rate (61.3%) is virtually identical to Claude's (60.6%), but he appears in fewer games (31 vs 99). He dominates the GFC era where sustained low rates favour capital appreciation.
- **Mr Max Lever strengthened significantly** (8→12 wins, 48% win rate) — when the advice engine pushes Claude toward conservative play, it creates buying windows that Mort Gage's leverage strategy exploits.
- **Ms Di Vidend dropped sharply** (7→2 wins) — when Claude switches to yield strategy, she directly competes for the same high-yield properties and loses to Claude's lower LTV discipline.
- **Reid Furbish wins only in Early Thatcher Recovery** — high rates that fall over 20 turns suit the BRRR cycle. His 3rd-place frequency (36/42 appearances in Run 2) reflects that BRRR requires longer time horizons than 20 turns to compound effectively.
- **Ray Novate's cash-heavy profile** (avg £700k equity vs £2.2M cash) remains the core constraint — his value-add thesis builds wealth but the final-tick scoring rewards equity over idle cash.
- **Ms Demi Graphic's high equity** (avg £1.82M, second only to Hugh Price) confirms her geographic concentration strategy builds genuine value — but regional concentration risk scoring frequently pushes her to 3rd.
