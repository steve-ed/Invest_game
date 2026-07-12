# Kivy UI Prototype — Design Spec

**Date:** 2026-06-29
**Scope:** Standalone Kivy prototype for RealEstGame. No engine integration — all screens use dummy data. Target platforms: PC (primary), Android/iOS (later).

---

## 1. Goals

- Prototype all 4 game screens in Kivy with dummy data
- Validate layout and visual style before engine wiring
- Establish file structure and widget patterns for future integration

---

## 2. Technology

- **Kivy** (pure, no KivyMD) with KV language for layout files
- Python 3.x, no additional UI dependencies
- KV files define widget trees; Python classes handle logic and screen transitions

---

## 3. Visual Style — Dark Command Centre

- Background: `#0a0e1a`
- Panel background: `#111827`
- Panel border: `#1f2937`
- Primary accent (positive/selected): `#00ff88`
- Warning/down: `#f87171`
- AI Conservative: `#fbbf24`
- AI Aggressive: `#f87171`
- Muted text: `#6b7280`
- Body text: `#9ca3af`
- Bright text: `#f9fafb`
- Font: monospace throughout

Trend arrows: `↑` in `#00ff88`, `↓` in `#f87171`, `→` in `#6b7280`

---

## 4. File Structure

```
ui_kivy/
├── main.py              # App entry point; builds ScreenManager with 4 screens
├── app.kv               # Root KV (imports all screen KVs)
├── dummy_data.py        # Static fake SimulationState used by all screens
├── screens/
│   ├── opening.py       # OpeningScreen class
│   ├── opening.kv
│   ├── turn.py          # TurnScreen class
│   ├── turn.kv
│   ├── decision.py      # DecisionScreen class
│   ├── decision.kv
│   ├── end.py           # EndScreen class
│   └── end.kv
└── widgets/
    ├── macro_sidebar.py # MacroSidebar reusable widget
    └── macro_sidebar.kv
```

---

## 5. Screens

### 5.1 Opening Screen (`opening`)

Shown once at game start. Read-only — no player input except START.

**Content:**
- Game title + mode label (10-year · 20 turns · 3 actors)
- Starting Positions table (Actor, Props, Portfolio, Cash) — all actors start at 0 props
- Starting Macro panel (Price Index, Interest Rate, Rent Growth)
- Available Market table (ID, Region, Value, Rent/mo, Yield) — scrollable if >5 rows
- `START GAME →` button → navigates to Turn screen

---

### 5.2 Turn Dashboard (`turn`)

Main per-turn view. Sidebar + stacked panels layout.

**Left sidebar (`MacroSidebar`):**
- Tick counter (large, green) + "of 20"
- Scenario name
- Price Index, Interest Rate, Rent Growth with trend arrows
- Current rank + score

**Right stacked panels:**
1. **YOUR PORTFOLIO** — total value (large green), cash, property list (ID, Region, Value, Rent/mo, Yield)
2. **AI POSITIONS** — one row per AI: name (colour-coded), prop count, portfolio value, last action
3. **NEWS** — last 2 events from `news` list (shocks, scenario transitions)

**Bottom right:** `MAKE DECISION →` button → navigates to Decision screen

---

### 5.3 Decision Screen (`decision`)

Player selects a property and an action.

**Left sidebar:** Same `MacroSidebar` widget, showing cash prominently at bottom.

**Right panels:**
1. **SELECT PROPERTY** — scrollable list of market properties. Affordable ones highlighted green; too-expensive ones dimmed. Selected property highlighted with `►`. Tapping/clicking selects it.
2. **YOUR ACTION** — three large buttons: `BUY`, `HOLD`, `SELL`. BUY is only active if a market property is selected and affordable. SELL is only active if player owns properties. `CONFIRM →` button submits.

**On CONFIRM:** increments `dummy_data` tick counter (wraps at 20 → End screen), navigates to Turn or End.

---

### 5.4 End Screen (`end`)

Shown when tick reaches 20 (or `total_ticks`).

**Content:**
- `GAME OVER` heading (gold) + summary (turns, years, actors)
- Final Leaderboard — rank, name, score. Winner row highlighted green.
- YOUR BREAKDOWN panel — Portfolio value, Cash, Cumulative rent
- KEY EVENTS panel — timestamped list of shocks and scenario transitions from dummy data
- `PLAY AGAIN` button → resets dummy data tick, navigates to Opening

---

## 6. MacroSidebar Widget

Reusable `BoxLayout` used on Turn and Decision screens.

**Properties (Python):**
- `tick: NumericProperty`
- `total_ticks: NumericProperty`
- `scenario: StringProperty`
- `price_index: NumericProperty`
- `price_trend: StringProperty`  — `"up"`, `"down"`, `"flat"`
- `rate: NumericProperty`
- `rate_trend: StringProperty`
- `rent_growth: NumericProperty`
- `rent_trend: StringProperty`
- `rank: NumericProperty`
- `score: NumericProperty`
- `cash: NumericProperty`  — shown on Decision screen only (optional)

Trend arrow and colour computed in KV using `price_trend` etc.

---

## 7. Dummy Data

`dummy_data.py` exports two dicts: `START_STATE` (tick 0, all actors at 0 props, used by Opening screen) and `GAME_STATE` (tick 4, mid-game, used by Turn/Decision screens). `PLAY AGAIN` resets `GAME_STATE["tick"]` to 1 and navigates to Opening. Decision screen writes `tick += 1` on CONFIRM.

```python
GAME_STATE = {
    "tick": 4, "total_ticks": 20, "scenario": "Recovery",
    "macro": {
        "price_index": 112.4, "rate": 4.5, "rent_growth": 3.2,
        "prev": {"price_index": 109.1, "rate": 5.0, "rent_growth": 2.8},
    },
    "player": {
        "cash": 42000,
        "portfolio": [
            {"id": "P-001", "region": "North", "value": 182000, "rent": 755},
            {"id": "P-004", "region": "East",  "value": 158000, "rent": 630},
        ],
    },
    "ai": [
        {"name": "Conservative", "cash": 30000, "portfolio_value": 410000, "last_action": "hold"},
        {"name": "Aggressive",   "cash": 15000, "portfolio_value": 520000, "last_action": "buy"},
    ],
    "market": [
        {"id": "P-002", "region": "West",  "value": 210000, "rent": 820},
        {"id": "P-005", "region": "North", "value": 340000, "rent": 1100},
        {"id": "P-009", "region": "East",  "value": 195000, "rent": 780},
    ],
    "news": ["⚡ Rate shock: +1% applied", "→ Scenario: Baseline → Recovery"],
    "leaderboard": [
        {"name": "You",          "score": 485200},
        {"name": "Aggressive",  "score": 520000},
        {"name": "Conservative","score": 410000},
    ],
}
```

---

## 8. Navigation Flow

```
Opening ──[START GAME]──► Turn ──[MAKE DECISION]──► Decision
                           ▲                              │
                           └──────[CONFIRM, tick<20]──────┘
                                         │
                                  [tick==20]
                                         │
                                        End ──[PLAY AGAIN]──► Opening
```

---

## 9. Out of Scope (prototype)

- Engine integration (no `kernel.py` calls)
- Live state updates / reactive data binding
- Scrollable history / sparklines
- Sound effects
- Android/iOS packaging (deferred to post-prototype)
- Persistence / save state
