# Player Choice — Strategy Sheet Design

## Purpose

A one-page sheet the reader completes while reading the book. Their answers
configure the simulation to match their actual situation — starting capital,
strategy, target LTV, yield, and time horizon — so the game teaches from
their position rather than a generic one.

The sheet exists in two forms: a printable page in Appendix K of the book
(completed during reading) and the game's opening screen (pre-populated from
those answers, overrideable before play begins).

---

## The Six Inputs That Matter

Everything else the reader knows about themselves is downstream of these six.
Region preference and stated risk tolerance are outputs of the mapping, not
inputs to it.

| Input | Options |
|---|---|
| Landlord experience | None / 1–2 years, 1–2 properties / 3+ years, 2+ properties |
| Renovation capacity | None / Some trades contacts / Experienced PM |
| Portfolio size | 0 / 1–2 properties / 3+ properties |
| Time horizon | Under 5 years / 5–10 years / 10+ years |
| Capital available | £ (total savings minus retained buffer) |
| Monthly headroom | £/month (cashflow shortfall absorbable from employment) |

---

## Strategy Mapping — Decision Tree

A scoring system creates false precision. A decision tree gives a deterministic
output for any honest reader.

```
No landlord experience?
├─ Renovation capacity = none or some → YIELD
└─ Renovation capacity = experienced PM → VALUE-ADD

1–2 years experience, 1–2 properties?
├─ Monthly headroom ≥ £300 AND time horizon ≥ 10 years → CAPITAL GROWTH
├─ Renovation capacity = experienced PM → BRRR
└─ Neither → YIELD  (build further before moving up)

3+ years experience, 2+ properties?
├─ Portfolio 3+ properties → DEMOGRAPHIC
├─ Portfolio < 3 properties, strong buffer, conviction market is rising → LEVERAGE
└─ Otherwise → BRRR or CAPITAL GROWTH (offer both; player chooses)
```

The only ambiguous node is the experienced investor without a 3+ property
portfolio. Present both options and let them choose — the sheet records which
they picked and why.

---

## Default Parameters by Strategy

These are the game's starting values when a strategy is selected. The player
can adjust on the opening screen before the first turn.

| Strategy | Target LTV | Target gross yield | Region default | Notes |
|---|---|---|---|---|
| Yield | 70% | 6.0%+ | North / Midlands | Defensive; income covers mortgage comfortably |
| Capital Growth | 75% | 4.5–5.0% | Major cities | Accepts thin cashflow; long hold |
| Value-Add | 65% | 5.0%+ post-upgrade | Any | Lower LTV funds upgrade capex |
| BRRR | 75% | 5.0%+ post-refi | Secondary markets | Requires below-market entry |
| Leverage | 80% | 4.5%+ | Primary markets | Maximum borrowing; rate-sensitive |
| Demographic | 70% | 5.5%+ | Mixed — 3+ regions | Spread risk; monitor regional demand |

---

## The Sheet — Appendix K Layout

One side of A4. Reader completes during or immediately after Chapter 4.

---

### Your Strategy Sheet

*Complete this before your first game. Your answers configure the simulation
to match your actual situation rather than a generic starting position.*

**Section 1 — Your Capital**

| | |
|---|---|
| Total savings available for property investment | £ |
| Buffer you will keep in reserve (not invested) | £ |
| **Capital available to invest** | £ |
| Monthly employment income (gross) | £ / month |
| Monthly shortfall you could absorb from other income | £ / month |

**Section 2 — Your Experience**

Circle one in each row:

| | | | |
|---|---|---|---|
| Landlord experience | None | 1–2 years / 1–2 properties | 3+ years / 2+ properties |
| Renovation capacity | None | Some trades contacts | Experienced PM |
| Portfolio size now | 0 properties | 1–2 properties | 3+ properties |
| Time horizon | Under 5 years | 5–10 years | 10+ years |

**Section 3 — Your Strategy**

Follow the tree on the back of this sheet. Circle your output:

**YIELD — CAPITAL GROWTH — VALUE-ADD — BRRR — LEVERAGE — DEMOGRAPHIC**

If you landed on two options: which did you choose and why?

_______________________________________________

**Section 4 — Your Game Parameters**

Transfer these to the opening screen when you start the simulation.

| Parameter | Your value |
|---|---|
| Starting capital | £ |
| Strategy | |
| Target LTV | % |
| Target gross yield | % |
| Time horizon | years |
| Region focus | |

---

## Game Opening Screen

The opening screen presents the strategy sheet fields as a short form,
pre-populated with the defaults for the detected or last-used strategy.
The player can adjust any field before starting.

**Fields:**

```
Strategy         [dropdown: Yield / Capital Growth / Value-Add / BRRR / Leverage / Demographic]
Starting capital [£ input — drives portfolio calibration]
Target LTV       [% slider: 60–85%]
Target yield     [% input]
Time horizon     [years: 5 / 10 / 15 / 20]
Region focus     [dropdown: North / Midlands / Wales-Scotland / Major cities / Mixed]
Era              [Auto (random) / Manual (year selector 1984–2014)]
```

A "Use my sheet" button above the form prompts the player to enter their
Section 4 values. Once entered, those values persist as their profile across
sessions — they are comparing each game against their own parameters, not
against a fixed benchmark.

---

## Config Format

The game reads and writes a player profile as JSON. This is what the opening
screen produces and what the simulation engine consumes.

```json
{
  "strategy": "yield",
  "capital": 75000,
  "ltv_target": 0.70,
  "yield_target": 0.06,
  "time_horizon": 10,
  "monthly_headroom": 300,
  "region": "north",
  "era": "auto"
}
```

The engine uses `capital` to calibrate starting portfolio value. The low-capital
variant (separate build) will use the same config format — the only difference
is that `capital` in the range £70,000–£90,000 triggers single-property
starting conditions rather than the established-investor scale.

---

## Design Decisions — Open

**1. Enforce or suggest?**
The sheet suggests a strategy; the opening screen lets the player override it.
The learning comes from comparing actual play against what the sheet prescribed.
Enforcing would remove the most useful friction. Recommend: suggest only.

**2. Profile persistence**
The player's sheet values should persist across sessions as their baseline.
After each game, show how the era they drew compares to what their strategy
was calibrated for — this is the connection between the sheet and the debrief
narrative (see era_conclusion_190726.md).

**3. Where does the decision tree live in the book?**
Currently it lives only in this spec. It should appear in Appendix K on the
back of the sheet so the reader can work through it without referring elsewhere.
The Chapter 4 strategy descriptions already provide the supporting argument.

---

## Connection to Debrief Narrative

The strategy sheet creates the context the debrief needs. Once the game knows
the player's strategy, their capital position, and their time horizon, the
end-of-game debrief can say:

*"You played Yield with £75,000 and a 10-year horizon, starting in 1991. That
era rewarded Demographic investors most (73% win rate). Yield produced a 50%
win rate in that era — defensible given your capital position, but the era
penalised income focus relative to regional diversification. In a repeat of
this era, consider whether your cashflow buffer would support a Demographic
approach."*

This is the fix identified in era_conclusion_190726.md: the debrief narrative
currently contradicts what the simulation rewards. The strategy sheet gives
the engine enough context to make the debrief personal and self-consistent.
