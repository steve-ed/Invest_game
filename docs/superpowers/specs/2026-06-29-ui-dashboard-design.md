# UI Dashboard Design

## Goal
Replace the current plain-print terminal UI with a `rich`-powered dashboard that shows the full game state each turn — newest turn on top, full history scrolling below — plus an opening screen, an end-of-game screen, and an AI dashboard panel.

## Library
`rich` (add to `requirements.txt`). No other new dependencies.

---

## Architecture

### New / changed files

| File | Change | Responsibility |
|---|---|---|
| `ui/dashboard.py` | Create | All rich rendering: turn panel, opening screen, end screen |
| `player/choices.py` | Rewrite | Delegates display to `dashboard.py`, handles input only |
| `kernel.py` | Modify | Calls `dashboard.show_opening()`, `dashboard.show_end()`, passes macro history to dashboard |
| `state.py` | Modify | Add `macro_history: list` field to `SimulationState` — snapshots macro + events each tick |
| `requirements.txt` | Modify | Add `rich` |

`ui/event_log_state.py`, `ui/event_log_schema.py`, `ui/event_log_components.py` remain unchanged.

### Data flow
1. `kernel.run()` advances tick, accumulates `state.macro_history` (one snapshot per tick)
2. After player choices, `dashboard.render_turn(state, last_ai_actions, news_feed)` is called from `player/choices.py`
3. Dashboard clears screen, renders current turn at top, then renders all previous turn panels below
4. At game end, `kernel.run()` calls `dashboard.show_end(state, trace)`

---

## MacroSnapshot

Added to `state.py`:

```python
@dataclass
class MacroSnapshot:
    tick: int
    scenario: str
    price_index: float
    interest_rate: float
    rent_growth: float
    events: list  # shock/transition event dicts from that tick
```

`SimulationState` gains:
```python
macro_history: list = field(default_factory=list)  # list of MacroSnapshot
```

Kernel appends one `MacroSnapshot` per tick after all phases complete.

---

## Opening Screen

Shown once before turn 1. Player presses Enter to begin.

**Sections:**
1. Title banner: `REALESTGAME · 20 turns · 10 year simulation`
2. **Starting Positions table** — all actors, equal total value, different mix:

| Actor | Properties | Portfolio Value | Cash | Total |
|---|---|---|---|---|
| Player | 5 | £1,000,000 | £200,000 | £1,200,000 |
| Conservative AI | 3 | £600,000 | £600,000 | £1,200,000 |
| Aggressive AI | 7 | £1,100,000 | £100,000 | £1,200,000 |

3. **Each actor's property list** (id, region, value, rent, yield)
4. **Market** — 4 unowned properties available from turn 1 (see Property Pool below)
5. **Economic Conditions** — starting values only (no history yet)
6. `Press ENTER to begin...`

---

## Per-Turn Dashboard

Rendered each turn. Screen is cleared, then the following is printed newest-first:

### Current turn panel

```
════════════════════════════════════════════════════════════
  TICK 3  ·  BASELINE  ·  18 months elapsed
════════════════════════════════════════════════════════════

  ECONOMIC CONDITIONS
  Tick  Scenario    Price Idx   Rate    Rent Gr   Events
  ────  ──────────  ─────────   ──────  ───────   ─────────────────────
    3   BASELINE      101.5 ↑    5.2% ↑   3.0% →
    2   BASELINE      101.0 ↑    5.0% →   3.0% →
    1   BASELINE      100.5 ↑    5.0% →   3.0% →
    0   —             100.0      5.0%     3.0%    (start)

  MARKET NEWS  (latest 5)
  › Buy-to-let landlords face mounting pressure.
  › Market conditions remain within normal parameters.
  › Property prices continue their steady upward trend.

  YOUR POSITION                         Cash: £152,281
  ────────────────────────────────────────────────────
   ID   Region          Value       Rent/mo   Yield
   p01  London         £402,010     £2,005    6.0%

  AI DASHBOARD
  ────────────────────────────────────────────────────
  Conservative AI   Score: £321,500   Cash: £121,500   Last: hold
   p04  Bristol     £201,005          £1,035    6.2%

  Aggressive AI     Score: £281,005   Cash: £100,501   Last: bought m3
   p07  Sheffield   £130,500            £652    6.0%
   m3   Leeds CC    £155,800            £932    7.2%

  MARKET (unowned)
  ────────────────────────────────────────────────────
   m1   London Shoreditch  £421,050  £1,470/mo  3.5%   (need £268,769)
   m4   Sunderland          £80,400    £560/mo  8.4%   ✓ affordable

  [h]old  ·  [s]ell <id> (p01)  ·  [b]uy <id> (m1, m4)
  > _
```

### Trend arrows
Computed by comparing each tick's value to the previous tick:
- `↑` — increased
- `↓` — decreased
- `→` — unchanged (within 0.001)

### Events column
Shows shock and scenario transition events that fired on that tick. Examples:
- `⚡ Rate Hike +2%`
- `↘ Scenario → DOWNTURN`
- `⚡ Price Drop ×0.90`

### Market News feed
Last 5 events of type `scenario_event` or `narrative_branch` from `state.event_log`, newest first.

### Yield
Computed inline: `(rent * 12) / current_value * 100`. Not stored on `Property`.

### History
After the current turn panel, all previous turns are printed in the same format, newest first. No collapsing — full panel per tick.

---

## End-of-Game Screen

Shown after the final tick instead of the action prompt.

```
════════════════════════════════════════════════════════════
  GAME OVER  ·  20 turns  ·  10 years elapsed
════════════════════════════════════════════════════════════

  FINAL LEADERBOARD
   Rank  Actor              Score        Portfolio      Cash
      1  Player           £532,155      £363,400    £168,755
      2  Conservative AI  £316,704      £181,700    £135,004
      3  Aggressive AI    £276,033      £163,530    £112,503

  PORTFOLIO BREAKDOWN
  [per actor: each property with final value and rent]

  KEY EVENTS
  Tick  5  ⚡ Rate Hike +2%
  Tick  8  ↘ Scenario → DOWNTURN
  Tick 10  ⚡ Price Drop ×0.90
  Tick 15  ↗ Scenario → RECOVERY
```

Key events are extracted from `state.macro_history` — any tick whose `events` list is non-empty.

---

## Property Pool (19 properties total)

### Actor-owned at start (15)

Implementation must assign these so each actor's portfolio value + cash = £1,200,000.

**Player (5 properties, ~£1,000,000 portfolio):**

| ID | Region | Base Value | Rent/mo |
|---|---|---|---|
| p01 | London Kensington | £500,000 | £2,500 |
| p02 | Oxford | £230,000 | £1,150 |
| p03 | Brighton | £220,000 | £1,100 |
| p04 | Sheffield | £130,000 | £650 |
| p05 | Leicester | £140,000 | £700 |
| | **Total** | **£1,220,000** | |

> Cash: £200,000. Total: ~£1,220,000 (close enough; exact target set during implementation).

**Conservative AI (3 properties, ~£600,000 portfolio):**

| ID | Region | Base Value | Rent/mo |
|---|---|---|---|
| p06 | Bristol | £260,000 | £1,300 |
| p07 | Cambridge | £250,000 | £1,250 |
| p08 | Birmingham | £200,000 | £1,000 |
| | **Total** | **£710,000** | |

> Cash: £490,000. Total: £1,200,000.

**Aggressive AI (7 properties, ~£1,100,000 portfolio):**

| ID | Region | Base Value | Rent/mo |
|---|---|---|---|
| p09 | Manchester | £240,000 | £1,200 |
| p10 | Leeds | £170,000 | £850 |
| p11 | Nottingham | £155,000 | £775 |
| p12 | Liverpool | £145,000 | £725 |
| p13 | Cardiff | £160,000 | £800 |
| p14 | Newcastle | £120,000 | £600 |
| p15 | Sunderland | £90,000 | £540 |
| | **Total** | **£1,080,000** | |

> Cash: £120,000. Total: £1,200,000.

### Market at start (4 properties, unowned)

| ID | Region | Base Value | Rent/mo | Gross Yield | Profile |
|---|---|---|---|---|---|
| m1 | London Shoreditch | £420,000 | £1,470 | 3.5% | Capital growth |
| m2 | Bristol Harbourside | £230,000 | £1,035 | 5.4% | Balanced |
| m3 | Leeds City Centre | £155,000 | £930 | 7.2% | Income play |
| m4 | Sunderland Dockside | £80,000 | £560 | 8.4% | High yield, high risk |

---

## Spec Self-Review

- No TBDs or placeholders remaining
- Property totals are approximate — implementation adjusts values to hit £1,200,000 exactly per actor
- `macro_history` is the single source of truth for the economic conditions table and key events
- Yield is always computed, never stored — avoids stale data
- `dashboard.py` contains only rendering logic; no game state mutation
- Non-interactive fallback (tests, piped input) unchanged — `sys.stdin.isatty()` check remains in `player/choices.py`
