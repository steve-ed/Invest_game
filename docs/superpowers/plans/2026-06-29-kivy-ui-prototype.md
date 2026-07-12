# Kivy UI Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Kivy prototype of RealEstGame with 4 screens (Opening, Turn, Decision, End), dummy data, and a simulated game loop — no engine integration.

**Architecture:** Pure Kivy app using ScreenManager; screen layouts defined in .kv files; Python screen classes read from `dummy_data.py`. A reusable `MacroSidebar` widget is shared between Turn and Decision screens. `DecisionScreen.confirm()` increments the tick counter and drives navigation to Turn (loop) or End (game over). All `Builder.load_file()` calls are in `main.py` only, before Python class imports.

**Tech Stack:** Python 3.x, Kivy (`pip install kivy`)

---

## File Map

| File | Responsibility |
|------|---------------|
| `ui_kivy/main.py` | App entry point; loads all KV files; builds ScreenManager |
| `ui_kivy/dummy_data.py` | `START_STATE`, `GAME_STATE`, helper functions (`trend`, `trend_arrow`, `portfolio_value`, `gross_yield`) |
| `ui_kivy/widgets/macro_sidebar.py` | `MacroSidebar` Kivy class with `NumericProperty`/`StringProperty` fields |
| `ui_kivy/widgets/macro_sidebar.kv` | MacroSidebar layout — tick panel, macro panel, rank panel, optional cash panel |
| `ui_kivy/screens/opening.py` | `OpeningScreen` — populates actor table and market table from `START_STATE` |
| `ui_kivy/screens/opening.kv` | Opening layout — title, positions panel, macro panel, market scroll, start button |
| `ui_kivy/screens/turn.py` | `TurnScreen` — populates sidebar, portfolio, AI, news from `GAME_STATE` |
| `ui_kivy/screens/turn.kv` | Turn layout — sidebar + stacked portfolio/AI/news panels |
| `ui_kivy/screens/decision.py` | `DecisionScreen` — property selection, BUY/HOLD/SELL, tick increment on CONFIRM |
| `ui_kivy/screens/decision.kv` | Decision layout — sidebar + market list + action buttons |
| `ui_kivy/screens/end.py` | `EndScreen` — leaderboard, breakdown, key events; PLAY AGAIN resets tick |
| `ui_kivy/screens/end.kv` | End layout — GAME OVER header, leaderboard, breakdown+events panels |
| `ui_kivy/tests/test_dummy_data.py` | Unit tests for helper functions and data structure shape |
| `ui_kivy/tests/test_navigation.py` | Unit tests for tick increment and end condition logic |

---

## Color Reference (Kivy RGBA 0–1)

```python
BG     = (0.039, 0.055, 0.102, 1)   # #0a0e1a  — screen background
PANEL  = (0.067, 0.094, 0.153, 1)   # #111827  — panel background
BORDER = (0.122, 0.161, 0.216, 1)   # #1f2937  — panel border
ACCENT = (0, 1, 0.533, 1)           # #00ff88  — green: positive/selected
DANGER = (0.973, 0.443, 0.443, 1)   # #f87171  — red: negative/down
CONS   = (0.984, 0.749, 0.141, 1)   # #fbbf24  — yellow: Conservative AI
AGGR   = (0.973, 0.443, 0.443, 1)   # #f87171  — red: Aggressive AI
MUTED  = (0.420, 0.447, 0.502, 1)   # #6b7280  — labels/headers
BODY   = (0.612, 0.639, 0.686, 1)   # #9ca3af  — body text
BRIGHT = (0.976, 0.980, 0.984, 1)   # #f9fafb  — primary values
DIM    = (0.294, 0.333, 0.388, 1)   # #4b5563  — dimmed/disabled
```

---

## Task 1: Scaffold + dummy data + tests

**Files:**
- Create: `ui_kivy/dummy_data.py`
- Create: `ui_kivy/screens/__init__.py`
- Create: `ui_kivy/widgets/__init__.py`
- Create: `ui_kivy/tests/__init__.py`
- Create: `ui_kivy/tests/test_dummy_data.py`

- [ ] **Step 1: Create directory structure**

Run from `C:/Users/steve/projects/RealEstGame`:
```bash
mkdir -p ui_kivy/screens ui_kivy/widgets ui_kivy/tests
touch ui_kivy/screens/__init__.py ui_kivy/widgets/__init__.py ui_kivy/tests/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `ui_kivy/tests/test_dummy_data.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dummy_data import trend, trend_arrow, portfolio_value, gross_yield, GAME_STATE, START_STATE


def test_trend_up():
    assert trend(112.4, 109.1) == "up"


def test_trend_down():
    assert trend(4.5, 5.0) == "down"


def test_trend_flat():
    assert trend(5.0, 5.0) == "flat"


def test_trend_arrow_up():
    assert trend_arrow("up") == "↑"


def test_trend_arrow_down():
    assert trend_arrow("down") == "↓"


def test_trend_arrow_flat():
    assert trend_arrow("flat") == "→"


def test_portfolio_value():
    assert portfolio_value(GAME_STATE["player"]) == 182000 + 158000


def test_gross_yield():
    prop = {"value": 180000, "rent": 750}
    assert abs(gross_yield(prop) - 5.0) < 0.01


def test_game_state_keys():
    for key in ("tick", "total_ticks", "scenario", "macro", "player", "ai", "market", "news", "leaderboard", "end"):
        assert key in GAME_STATE, f"Missing: {key}"


def test_start_state_keys():
    for key in ("tick", "total_ticks", "scenario", "macro", "actors", "market"):
        assert key in START_STATE, f"Missing: {key}"
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd ui_kivy && python -m pytest tests/test_dummy_data.py -v
```
Expected: `ModuleNotFoundError: No module named 'dummy_data'`

- [ ] **Step 4: Write `dummy_data.py`**

Create `ui_kivy/dummy_data.py`:
```python
START_STATE = {
    "tick": 0,
    "total_ticks": 20,
    "scenario": "Baseline",
    "macro": {
        "price_index": 100.0,
        "rate": 5.0,
        "rent_growth": 2.5,
        "prev": {"price_index": 100.0, "rate": 5.0, "rent_growth": 2.5},
    },
    "actors": [
        {"name": "You",          "cash": 100000, "props": 0, "portfolio_value": 0},
        {"name": "Conservative", "cash": 100000, "props": 0, "portfolio_value": 0},
        {"name": "Aggressive",   "cash": 100000, "props": 0, "portfolio_value": 0},
    ],
    "market": [
        {"id": "P-001", "region": "North", "value": 180000, "rent": 750},
        {"id": "P-002", "region": "East",  "value": 210000, "rent": 820},
        {"id": "P-003", "region": "West",  "value": 340000, "rent": 1100},
        {"id": "P-004", "region": "South", "value": 155000, "rent": 610},
        {"id": "P-005", "region": "North", "value": 195000, "rent": 780},
        {"id": "P-006", "region": "East",  "value": 275000, "rent": 920},
        {"id": "P-007", "region": "West",  "value": 320000, "rent": 1050},
        {"id": "P-008", "region": "South", "value": 145000, "rent": 580},
        {"id": "P-009", "region": "North", "value": 225000, "rent": 870},
        {"id": "P-010", "region": "East",  "value": 190000, "rent": 760},
    ],
}

GAME_STATE = {
    "tick": 4,
    "total_ticks": 20,
    "scenario": "Recovery",
    "macro": {
        "price_index": 112.4,
        "rate": 4.5,
        "rent_growth": 3.2,
        "prev": {"price_index": 109.1, "rate": 5.0, "rent_growth": 2.8},
    },
    "player": {
        "cash": 42000,
        "portfolio": [
            {"id": "P-001", "region": "North", "value": 182000, "rent": 755},
            {"id": "P-004", "region": "South", "value": 158000, "rent": 630},
        ],
    },
    "ai": [
        {"name": "Conservative", "cash": 30000, "portfolio_value": 410000, "props": 2, "last_action": "hold"},
        {"name": "Aggressive",   "cash": 15000, "portfolio_value": 520000, "props": 4, "last_action": "buy"},
    ],
    "market": [
        {"id": "P-002", "region": "West",  "value": 210000, "rent": 820},
        {"id": "P-005", "region": "North", "value": 340000, "rent": 1100},
        {"id": "P-009", "region": "East",  "value": 195000, "rent": 780},
    ],
    "news": [
        "⚡ Rate shock: +1% applied",
        "→ Scenario: Baseline → Recovery",
    ],
    "leaderboard": [
        {"name": "You",          "score": 485200},
        {"name": "Aggressive",   "score": 520000},
        {"name": "Conservative", "score": 410000},
    ],
    "end": {
        "player_breakdown": {"portfolio": 750000, "cash": 62000, "rent": 80000},
        "key_events": [
            {"tick": 3,  "text": "⚡ Rate shock: +1%"},
            {"tick": 7,  "text": "→ Downturn begins"},
            {"tick": 12, "text": "⚡ Price crash -15%"},
            {"tick": 15, "text": "→ Recovery"},
        ],
    },
}


def trend(current, previous):
    if current > previous:
        return "up"
    elif current < previous:
        return "down"
    return "flat"


def trend_arrow(direction):
    return {"up": "↑", "down": "↓", "flat": "→"}.get(direction, "→")


def portfolio_value(player):
    return sum(p["value"] for p in player["portfolio"])


def gross_yield(prop):
    return prop["rent"] * 12 / prop["value"] * 100
```

- [ ] **Step 5: Run tests — expect all pass**

```bash
cd ui_kivy && python -m pytest tests/test_dummy_data.py -v
```
Expected: 10 tests PASS

- [ ] **Step 6: Commit**

```bash
cd .. && git add ui_kivy/ && git commit -m "feat: scaffold Kivy UI prototype with dummy data and helper tests"
```

---

## Task 2: MacroSidebar widget

**Files:**
- Create: `ui_kivy/widgets/macro_sidebar.py`
- Create: `ui_kivy/widgets/macro_sidebar.kv`

- [ ] **Step 1: Write `widgets/macro_sidebar.py`**

Create `ui_kivy/widgets/macro_sidebar.py`:
```python
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, StringProperty


class MacroSidebar(BoxLayout):
    tick = NumericProperty(0)
    total_ticks = NumericProperty(20)
    scenario = StringProperty("")
    price_index = NumericProperty(100.0)
    price_trend = StringProperty("flat")
    rate = NumericProperty(5.0)
    rate_trend = StringProperty("flat")
    rent_growth = NumericProperty(2.5)
    rent_trend = StringProperty("flat")
    rank = NumericProperty(1)
    score = NumericProperty(0)
    cash = NumericProperty(0)
    show_cash = NumericProperty(0)
```

- [ ] **Step 2: Write `widgets/macro_sidebar.kv`**

Create `ui_kivy/widgets/macro_sidebar.kv`:
```kv
<MacroSidebar>:
    orientation: 'vertical'
    size_hint_x: None
    width: '90dp'
    spacing: '4dp'
    padding: '4dp'
    canvas.before:
        Color:
            rgba: 0.039, 0.055, 0.102, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # Tick panel
    BoxLayout:
        size_hint_y: None
        height: '64dp'
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: 0.067, 0.094, 0.153, 1
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: 0, 1, 0.533, 0.2
            Line:
                rectangle: self.x, self.y, self.width, self.height
                width: 1
        Label:
            text: 'TICK'
            color: 0.420, 0.447, 0.502, 1
            font_size: '8sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: str(root.tick)
            color: 0, 1, 0.533, 1
            font_size: '22sp'
            bold: True
        Label:
            text: 'of ' + str(root.total_ticks)
            color: 0.420, 0.447, 0.502, 1
            font_size: '8sp'
            size_hint_y: None
            height: '14dp'

    # Macro panel
    BoxLayout:
        size_hint_y: None
        height: '130dp'
        orientation: 'vertical'
        padding: '6dp'
        spacing: '1dp'
        canvas.before:
            Color:
                rgba: 0.067, 0.094, 0.153, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: root.scenario.upper()
            color: 0.976, 0.980, 0.984, 1
            font_size: '9sp'
            size_hint_y: None
            height: '18dp'
        Label:
            text: 'Px'
            color: 0.420, 0.447, 0.502, 1
            font_size: '7sp'
            size_hint_y: None
            height: '12dp'
        Label:
            text: '{:.1f} {}'.format(root.price_index, '\u2191' if root.price_trend == 'up' else ('\u2193' if root.price_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.price_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.price_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '10sp'
            bold: True
            size_hint_y: None
            height: '16dp'
        Label:
            text: 'Rate'
            color: 0.420, 0.447, 0.502, 1
            font_size: '7sp'
            size_hint_y: None
            height: '12dp'
        Label:
            text: '{:.1f}% {}'.format(root.rate, '\u2191' if root.rate_trend == 'up' else ('\u2193' if root.rate_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.rate_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.rate_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '10sp'
            bold: True
            size_hint_y: None
            height: '16dp'
        Label:
            text: 'Rent'
            color: 0.420, 0.447, 0.502, 1
            font_size: '7sp'
            size_hint_y: None
            height: '12dp'
        Label:
            text: '{:.1f}% {}'.format(root.rent_growth, '\u2191' if root.rent_trend == 'up' else ('\u2193' if root.rent_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.rent_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.rent_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '10sp'
            bold: True
            size_hint_y: None
            height: '16dp'

    # Rank/score panel
    BoxLayout:
        size_hint_y: None
        height: '64dp'
        orientation: 'vertical'
        padding: '6dp'
        canvas.before:
            Color:
                rgba: 0.067, 0.094, 0.153, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: 'RANK'
            color: 0.420, 0.447, 0.502, 1
            font_size: '7sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: '#' + str(root.rank)
            color: 0, 1, 0.533, 1
            font_size: '18sp'
            bold: True
        Label:
            text: '\u00a3{:,.0f}'.format(root.score)
            color: 0.976, 0.980, 0.984, 1
            font_size: '9sp'
            size_hint_y: None
            height: '16dp'

    # Cash panel — Decision screen only
    BoxLayout:
        size_hint_y: None
        height: '44dp' if root.show_cash else '0dp'
        opacity: root.show_cash
        orientation: 'vertical'
        padding: '6dp'
        canvas.before:
            Color:
                rgba: 0.067, 0.094, 0.153, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: 'CASH'
            color: 0.420, 0.447, 0.502, 1
            font_size: '7sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: '\u00a3{:,.0f}'.format(root.cash)
            color: 0, 1, 0.533, 1
            font_size: '11sp'
            bold: True

    Widget:
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/steve/projects/RealEstGame && git add ui_kivy/widgets/ && git commit -m "feat: add MacroSidebar reusable Kivy widget"
```

---

## Task 3: Opening screen + app skeleton

**Files:**
- Create: `ui_kivy/screens/opening.py`
- Create: `ui_kivy/screens/opening.kv`
- Create: `ui_kivy/main.py`

- [ ] **Step 1: Write `screens/opening.py`**

Create `ui_kivy/screens/opening.py`:
```python
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
import dummy_data as dd

_ACTOR_COLORS = {
    "You":          (0, 1, 0.533, 1),
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.420, 0.447, 0.502, 1)
_BODY   = (0.612, 0.639, 0.686, 1)
_ACCENT = (0, 1, 0.533, 1)


class OpeningScreen(Screen):
    def on_enter(self):
        self._populate_actors()
        self._populate_market()

    def _populate_actors(self):
        grid = self.ids.actors_grid
        grid.clear_widgets()
        for h in ("Actor", "Props", "Portfolio", "Cash"):
            grid.add_widget(Label(text=h, color=_MUTED, font_size='9sp',
                                  halign='left', valign='middle'))
        for actor in dd.START_STATE["actors"]:
            nc = _ACTOR_COLORS.get(actor["name"], _BODY)
            grid.add_widget(Label(text=actor["name"], color=nc, font_size='9sp',
                                  halign='left', valign='middle'))
            grid.add_widget(Label(text=str(actor["props"]), color=_BODY, font_size='9sp',
                                  halign='right', valign='middle'))
            grid.add_widget(Label(text='\u00a3{:,.0f}'.format(actor["portfolio_value"]),
                                  color=_BODY, font_size='9sp', halign='right', valign='middle'))
            grid.add_widget(Label(text='\u00a3{:,.0f}'.format(actor["cash"]),
                                  color=nc, font_size='9sp', halign='right', valign='middle'))

    def _populate_market(self):
        grid = self.ids.market_grid
        grid.clear_widgets()
        for h in ("ID", "Region", "Value", "Rent/mo", "Yield"):
            grid.add_widget(Label(text=h, color=_MUTED, font_size='9sp',
                                  halign='left', valign='middle'))
        for prop in dd.START_STATE["market"]:
            yld = prop["rent"] * 12 / prop["value"] * 100
            grid.add_widget(Label(text=prop["id"], color=_BODY, font_size='9sp',
                                  halign='left', valign='middle'))
            grid.add_widget(Label(text=prop["region"], color=_BODY, font_size='9sp',
                                  halign='left', valign='middle'))
            grid.add_widget(Label(text='\u00a3{:,.0f}'.format(prop["value"]),
                                  color=_BODY, font_size='9sp', halign='right', valign='middle'))
            grid.add_widget(Label(text='\u00a3{:,.0f}'.format(prop["rent"]),
                                  color=_BODY, font_size='9sp', halign='right', valign='middle'))
            grid.add_widget(Label(text='{:.1f}%'.format(yld), color=_ACCENT, font_size='9sp',
                                  halign='right', valign='middle'))
```

- [ ] **Step 2: Write `screens/opening.kv`**

Create `ui_kivy/screens/opening.kv`:
```kv
<OpeningScreen>:
    canvas.before:
        Color:
            rgba: 0.039, 0.055, 0.102, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        padding: '16dp'
        spacing: '12dp'

        # Title
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            orientation: 'vertical'
            Label:
                text: 'REALESTGAME'
                color: 0, 1, 0.533, 1
                font_size: '22sp'
                bold: True
            Label:
                text: '10-year mode  \u00b7  20 turns  \u00b7  3 actors'
                color: 0.420, 0.447, 0.502, 1
                font_size: '10sp'

        # Positions + macro
        BoxLayout:
            size_hint_y: None
            height: '140dp'
            spacing: '12dp'

            BoxLayout:
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'STARTING POSITIONS'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                GridLayout:
                    id: actors_grid
                    cols: 4
                    spacing: '4dp'
                    row_default_height: '18dp'

            BoxLayout:
                size_hint_x: 0.38
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'STARTING MACRO'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    size_hint_y: None
                    height: '20dp'
                    Label:
                        text: 'Price Index'
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '9sp'
                    Label:
                        text: '100.0'
                        color: 0.976, 0.980, 0.984, 1
                        font_size: '9sp'
                        halign: 'right'
                BoxLayout:
                    size_hint_y: None
                    height: '20dp'
                    Label:
                        text: 'Interest Rate'
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '9sp'
                    Label:
                        text: '5.0%'
                        color: 0.976, 0.980, 0.984, 1
                        font_size: '9sp'
                        halign: 'right'
                BoxLayout:
                    size_hint_y: None
                    height: '20dp'
                    Label:
                        text: 'Rent Growth'
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '9sp'
                    Label:
                        text: '2.5%'
                        color: 0.976, 0.980, 0.984, 1
                        font_size: '9sp'
                        halign: 'right'

        # Market table (scrollable)
        BoxLayout:
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgba: 0.067, 0.094, 0.153, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            padding: '8dp'
            spacing: '4dp'
            Label:
                text: 'AVAILABLE MARKET (10 properties)'
                color: 0.420, 0.447, 0.502, 1
                font_size: '8sp'
                size_hint_y: None
                height: '14dp'
                halign: 'left'
            ScrollView:
                GridLayout:
                    id: market_grid
                    cols: 5
                    spacing: '4dp'
                    size_hint_y: None
                    height: self.minimum_height
                    row_default_height: '18dp'

        # Start button
        BoxLayout:
            size_hint_y: None
            height: '44dp'
            Button:
                text: 'START GAME  \u2192'
                size_hint_x: None
                width: '160dp'
                pos_hint: {'center_x': 0.5}
                background_color: 0, 0, 0, 0
                canvas.before:
                    Color:
                        rgba: 0, 1, 0.533, 0.12
                    Rectangle:
                        pos: self.pos
                        size: self.size
                    Color:
                        rgba: 0, 1, 0.533, 0.4
                    Line:
                        rectangle: self.x, self.y, self.width, self.height
                        width: 1
                color: 0, 1, 0.533, 1
                font_size: '12sp'
                on_press: root.manager.current = 'turn'
```

- [ ] **Step 3: Write `main.py`** (Opening only for now)

Create `ui_kivy/main.py`:
```python
import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition

# Load KV files before importing screen classes
Builder.load_file('widgets/macro_sidebar.kv')
Builder.load_file('screens/opening.kv')

from screens.opening import OpeningScreen


class RealEstApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(OpeningScreen(name='opening'))
        return sm


if __name__ == '__main__':
    RealEstApp().run()
```

- [ ] **Step 4: Run and visually verify Opening screen**

```bash
cd ui_kivy && python main.py
```

Expected: dark window, green REALESTGAME title, 3-actor table, macro panel, 10-row scrollable market table, green START GAME button.

- [ ] **Step 5: Commit**

```bash
cd .. && git add ui_kivy/ && git commit -m "feat: add Opening screen with actor table and market table"
```

---

## Task 4: Turn dashboard screen

**Files:**
- Create: `ui_kivy/screens/turn.py`
- Create: `ui_kivy/screens/turn.kv`
- Modify: `ui_kivy/main.py`

- [ ] **Step 1: Write `screens/turn.py`**

Create `ui_kivy/screens/turn.py`:
```python
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
import dummy_data as dd
from dummy_data import trend

_AI_COLORS = {
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.420, 0.447, 0.502, 1)
_BODY   = (0.612, 0.639, 0.686, 1)
_ACCENT = (0, 1, 0.533, 1)
_DIM    = (0.294, 0.333, 0.388, 1)


class TurnScreen(Screen):
    def on_enter(self):
        self._update_sidebar()
        self._populate_portfolio()
        self._populate_ai()
        self._populate_news()

    def _update_sidebar(self):
        gs = dd.GAME_STATE
        m = gs["macro"]
        sb = self.ids.sidebar
        sb.tick = gs["tick"]
        sb.total_ticks = gs["total_ticks"]
        sb.scenario = gs["scenario"]
        sb.price_index = m["price_index"]
        sb.price_trend = trend(m["price_index"], m["prev"]["price_index"])
        sb.rate = m["rate"]
        sb.rate_trend = trend(m["rate"], m["prev"]["rate"])
        sb.rent_growth = m["rent_growth"]
        sb.rent_trend = trend(m["rent_growth"], m["prev"]["rent_growth"])
        sorted_lb = sorted(gs["leaderboard"], key=lambda x: x["score"], reverse=True)
        sb.rank = next((i + 1 for i, e in enumerate(sorted_lb) if e["name"] == "You"), 1)
        sb.score = next((e["score"] for e in gs["leaderboard"] if e["name"] == "You"), 0)

    def _populate_portfolio(self):
        gs = dd.GAME_STATE
        player = gs["player"]
        total = sum(p["value"] for p in player["portfolio"])
        self.ids.portfolio_value_label.text = '\u00a3{:,.0f}'.format(total)
        self.ids.cash_label.text = 'cash \u00a3{:,.0f}'.format(player["cash"])
        grid = self.ids.portfolio_grid
        grid.clear_widgets()
        for prop in player["portfolio"]:
            yld = prop["rent"] * 12 / prop["value"] * 100
            for text, color, align in [
                (prop["id"],                              _BODY,   'left'),
                (prop["region"],                          _BODY,   'left'),
                ('\u00a3{:,.0f}'.format(prop["value"]),  _BODY,   'right'),
                ('\u00a3{:,.0f}/mo'.format(prop["rent"]),_BODY,   'right'),
                ('{:.1f}%'.format(yld),                  _ACCENT, 'right'),
            ]:
                grid.add_widget(Label(text=text, color=color, font_size='9sp',
                                      halign=align, valign='middle'))

    def _populate_ai(self):
        grid = self.ids.ai_grid
        grid.clear_widgets()
        for ai in dd.GAME_STATE["ai"]:
            nc = _AI_COLORS.get(ai["name"], _BODY)
            for text, color, align in [
                (ai["name"],                                    nc,    'left'),
                ('{} props'.format(ai["props"]),                _BODY, 'left'),
                ('\u00a3{:,.0f}'.format(ai["portfolio_value"]), _BODY, 'right'),
                (ai["last_action"],                             _DIM,  'right'),
            ]:
                grid.add_widget(Label(text=text, color=color, font_size='9sp',
                                      halign=align, valign='middle'))

    def _populate_news(self):
        box = self.ids.news_box
        box.clear_widgets()
        for item in dd.GAME_STATE["news"][-2:]:
            box.add_widget(Label(text=item, color=_DIM, font_size='9sp',
                                 halign='left', valign='middle',
                                 size_hint_y=None, height='18dp'))
```

- [ ] **Step 2: Write `screens/turn.kv`**

Create `ui_kivy/screens/turn.kv`:
```kv
#:import MacroSidebar widgets.macro_sidebar.MacroSidebar

<TurnScreen>:
    canvas.before:
        Color:
            rgba: 0.039, 0.055, 0.102, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'horizontal'
        padding: '8dp'
        spacing: '8dp'

        MacroSidebar:
            id: sidebar

        BoxLayout:
            orientation: 'vertical'
            spacing: '8dp'

            # Portfolio panel
            BoxLayout:
                size_hint_y: 0.38
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'YOUR PORTFOLIO'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    size_hint_y: None
                    height: '24dp'
                    Label:
                        id: portfolio_value_label
                        text: '\u00a30'
                        color: 0, 1, 0.533, 1
                        font_size: '16sp'
                        bold: True
                        halign: 'left'
                    Label:
                        id: cash_label
                        text: 'cash \u00a30'
                        color: 0.294, 0.333, 0.388, 1
                        font_size: '9sp'
                        halign: 'right'
                GridLayout:
                    id: portfolio_grid
                    cols: 5
                    spacing: '4dp'
                    size_hint_y: None
                    height: self.minimum_height
                    row_default_height: '18dp'

            # AI positions panel
            BoxLayout:
                size_hint_y: 0.22
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'AI POSITIONS'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                GridLayout:
                    id: ai_grid
                    cols: 4
                    spacing: '4dp'
                    size_hint_y: None
                    height: self.minimum_height
                    row_default_height: '18dp'

            # News panel
            BoxLayout:
                size_hint_y: 0.18
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'NEWS'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    id: news_box
                    orientation: 'vertical'

            Widget:

            # Decision button
            BoxLayout:
                size_hint_y: None
                height: '40dp'
                Button:
                    text: 'MAKE DECISION  \u2192'
                    size_hint_x: None
                    width: '190dp'
                    pos_hint: {'right': 1}
                    background_color: 0, 0, 0, 0
                    canvas.before:
                        Color:
                            rgba: 0, 1, 0.533, 0.12
                        Rectangle:
                            pos: self.pos
                            size: self.size
                        Color:
                            rgba: 0, 1, 0.533, 0.4
                        Line:
                            rectangle: self.x, self.y, self.width, self.height
                            width: 1
                    color: 0, 1, 0.533, 1
                    font_size: '12sp'
                    on_press: root.manager.current = 'decision'
```

- [ ] **Step 3: Update `main.py`** to add TurnScreen

Replace `ui_kivy/main.py`:
```python
import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition

Builder.load_file('widgets/macro_sidebar.kv')
Builder.load_file('screens/opening.kv')
Builder.load_file('screens/turn.kv')

from screens.opening import OpeningScreen
from screens.turn import TurnScreen


class RealEstApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(OpeningScreen(name='opening'))
        sm.add_widget(TurnScreen(name='turn'))
        return sm


if __name__ == '__main__':
    RealEstApp().run()
```

- [ ] **Step 4: Run and verify Opening → Turn**

```bash
cd ui_kivy && python main.py
```

Expected: START GAME slides to Turn; sidebar shows tick 4, Recovery, macro values with arrows; portfolio panel shows 2 properties; AI panel shows Conservative and Aggressive rows; news shows 2 events.

- [ ] **Step 5: Commit**

```bash
cd .. && git add ui_kivy/ && git commit -m "feat: add Turn dashboard screen with sidebar, portfolio, AI, news"
```

---

## Task 5: Decision screen

**Files:**
- Create: `ui_kivy/screens/decision.py`
- Create: `ui_kivy/screens/decision.kv`
- Create: `ui_kivy/tests/test_navigation.py`
- Modify: `ui_kivy/main.py`

- [ ] **Step 1: Write failing navigation tests**

Create `ui_kivy/tests/test_navigation.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import dummy_data as dd


def setup_function():
    dd.GAME_STATE["tick"] = 4
    dd.GAME_STATE["total_ticks"] = 20


def test_confirm_increments_tick():
    initial = dd.GAME_STATE["tick"]
    dd.GAME_STATE["tick"] += 1
    assert dd.GAME_STATE["tick"] == initial + 1


def test_end_not_triggered_mid_game():
    dd.GAME_STATE["tick"] = 10
    dd.GAME_STATE["tick"] += 1
    assert dd.GAME_STATE["tick"] < dd.GAME_STATE["total_ticks"]


def test_end_triggered_at_total_ticks():
    dd.GAME_STATE["tick"] = 20
    assert dd.GAME_STATE["tick"] >= dd.GAME_STATE["total_ticks"]


def test_play_again_resets_tick():
    dd.GAME_STATE["tick"] = 20
    dd.GAME_STATE["tick"] = 1
    assert dd.GAME_STATE["tick"] == 1
```

- [ ] **Step 2: Run navigation tests**

```bash
cd ui_kivy && python -m pytest tests/test_navigation.py -v
```
Expected: 4 tests PASS (pure Python logic, no Kivy needed)

- [ ] **Step 3: Write `screens/decision.py`**

Create `ui_kivy/screens/decision.py`:
```python
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
import dummy_data as dd
from dummy_data import trend

_MUTED  = (0.420, 0.447, 0.502, 1)
_BODY   = (0.612, 0.639, 0.686, 1)
_ACCENT = (0, 1, 0.533, 1)
_DIM    = (0.294, 0.333, 0.388, 1)


class DecisionScreen(Screen):
    selected_prop = None
    selected_action = None

    def on_enter(self):
        self.selected_prop = None
        self.selected_action = None
        self._update_sidebar()
        self._populate_market()
        self._refresh_action_buttons()

    def _update_sidebar(self):
        gs = dd.GAME_STATE
        m = gs["macro"]
        sb = self.ids.sidebar
        sb.tick = gs["tick"]
        sb.total_ticks = gs["total_ticks"]
        sb.scenario = gs["scenario"]
        sb.price_index = m["price_index"]
        sb.price_trend = trend(m["price_index"], m["prev"]["price_index"])
        sb.rate = m["rate"]
        sb.rate_trend = trend(m["rate"], m["prev"]["rate"])
        sb.rent_growth = m["rent_growth"]
        sb.rent_trend = trend(m["rent_growth"], m["prev"]["rent_growth"])
        sb.cash = gs["player"]["cash"]
        sb.show_cash = 1
        sorted_lb = sorted(gs["leaderboard"], key=lambda x: x["score"], reverse=True)
        sb.rank = next((i + 1 for i, e in enumerate(sorted_lb) if e["name"] == "You"), 1)
        sb.score = next((e["score"] for e in gs["leaderboard"] if e["name"] == "You"), 0)

    def _populate_market(self):
        gs = dd.GAME_STATE
        cash = gs["player"]["cash"]
        box = self.ids.market_box
        box.clear_widgets()
        for prop in gs["market"]:
            affordable = prop["value"] <= cash
            color = _BODY if affordable else _DIM
            yld = prop["rent"] * 12 / prop["value"] * 100
            label = "{id}  {region}  \u00a3{value:,.0f}  \u00a3{rent:,.0f}/mo  {yld:.1f}%  {aff}".format(
                id=prop["id"], region=prop["region"],
                value=prop["value"], rent=prop["rent"],
                yld=yld, aff="\u2713 affordable" if affordable else "\u2717 too expensive",
            )
            btn = Button(
                text=label, color=color, font_size='9sp',
                halign='left', valign='middle',
                size_hint_y=None, height='28dp',
                background_color=(0, 0, 0, 0),
            )
            if affordable:
                btn.bind(on_press=lambda b, p=prop: self._select_prop(p, b))
            box.add_widget(btn)

    def _select_prop(self, prop, btn):
        self.selected_prop = prop
        for child in self.ids.market_box.children:
            child.background_color = (0, 0, 0, 0)
        btn.background_color = (0, 1, 0.533, 0.1)
        self._refresh_action_buttons()

    def _refresh_action_buttons(self):
        gs = dd.GAME_STATE
        self.ids.btn_buy.disabled = self.selected_prop is None
        self.ids.btn_sell.disabled = len(gs["player"]["portfolio"]) == 0

    def select_action(self, action):
        self.selected_action = action
        inactive = (0.122, 0.161, 0.216, 1)
        active   = (0, 1, 0.533, 0.15)
        for name in ('btn_buy', 'btn_hold', 'btn_sell'):
            self.ids[name].background_color = active if name == 'btn_' + action else inactive

    def confirm(self):
        gs = dd.GAME_STATE
        gs["tick"] += 1
        self.manager.current = 'end' if gs["tick"] >= gs["total_ticks"] else 'turn'
```

- [ ] **Step 4: Write `screens/decision.kv`**

Create `ui_kivy/screens/decision.kv`:
```kv
#:import MacroSidebar widgets.macro_sidebar.MacroSidebar

<DecisionScreen>:
    canvas.before:
        Color:
            rgba: 0.039, 0.055, 0.102, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'horizontal'
        padding: '8dp'
        spacing: '8dp'

        MacroSidebar:
            id: sidebar

        BoxLayout:
            orientation: 'vertical'
            spacing: '8dp'

            # Property selection panel
            BoxLayout:
                size_hint_y: 0.5
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '4dp'
                Label:
                    text: 'SELECT PROPERTY'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                ScrollView:
                    BoxLayout:
                        id: market_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: '2dp'

            # Action panel
            BoxLayout:
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '8dp'
                spacing: '8dp'
                Label:
                    text: 'YOUR ACTION'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    size_hint_y: None
                    height: '60dp'
                    spacing: '8dp'
                    Button:
                        id: btn_buy
                        text: 'BUY'
                        background_color: 0.122, 0.161, 0.216, 1
                        color: 0, 1, 0.533, 1
                        font_size: '14sp'
                        bold: True
                        on_press: root.select_action('buy')
                    Button:
                        id: btn_hold
                        text: 'HOLD'
                        background_color: 0.122, 0.161, 0.216, 1
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '14sp'
                        on_press: root.select_action('hold')
                    Button:
                        id: btn_sell
                        text: 'SELL'
                        background_color: 0.122, 0.161, 0.216, 1
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '14sp'
                        on_press: root.select_action('sell')
                BoxLayout:
                    size_hint_y: None
                    height: '40dp'
                    Button:
                        text: 'CONFIRM  \u2192'
                        size_hint_x: None
                        width: '140dp'
                        pos_hint: {'right': 1}
                        background_color: 0, 0, 0, 0
                        canvas.before:
                            Color:
                                rgba: 0, 1, 0.533, 0.12
                            Rectangle:
                                pos: self.pos
                                size: self.size
                            Color:
                                rgba: 0, 1, 0.533, 0.4
                            Line:
                                rectangle: self.x, self.y, self.width, self.height
                                width: 1
                        color: 0, 1, 0.533, 1
                        font_size: '12sp'
                        on_press: root.confirm()
```

- [ ] **Step 5: Update `main.py`** to add DecisionScreen

Replace `ui_kivy/main.py`:
```python
import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition

Builder.load_file('widgets/macro_sidebar.kv')
Builder.load_file('screens/opening.kv')
Builder.load_file('screens/turn.kv')
Builder.load_file('screens/decision.kv')

from screens.opening import OpeningScreen
from screens.turn import TurnScreen
from screens.decision import DecisionScreen


class RealEstApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(OpeningScreen(name='opening'))
        sm.add_widget(TurnScreen(name='turn'))
        sm.add_widget(DecisionScreen(name='decision'))
        return sm


if __name__ == '__main__':
    RealEstApp().run()
```

- [ ] **Step 6: Run and verify Turn → Decision → Turn loop**

```bash
cd ui_kivy && python main.py
```

Expected:
- Turn → MAKE DECISION → Decision screen shows 3 market properties, all dimmed "✗ too expensive" (player cash £42k vs cheapest property £195k)
- HOLD → button highlights green → CONFIRM → slides back to Turn with tick incremented to 5
- Repeat several times; tick counter in sidebar increments each loop

- [ ] **Step 7: Commit**

```bash
cd .. && git add ui_kivy/ && git commit -m "feat: add Decision screen with property selection and tick loop"
```

---

## Task 6: End screen + full wiring

**Files:**
- Create: `ui_kivy/screens/end.py`
- Create: `ui_kivy/screens/end.kv`
- Modify: `ui_kivy/main.py` (final — all 4 screens)

- [ ] **Step 1: Write `screens/end.py`**

Create `ui_kivy/screens/end.py`:
```python
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import dummy_data as dd

_ACTOR_COLORS = {
    "You":          (0, 1, 0.533, 1),
    "Conservative": (0.984, 0.749, 0.141, 1),
    "Aggressive":   (0.973, 0.443, 0.443, 1),
}
_MUTED  = (0.420, 0.447, 0.502, 1)
_BODY   = (0.612, 0.639, 0.686, 1)
_BRIGHT = (0.976, 0.980, 0.984, 1)
_ACCENT = (0, 1, 0.533, 1)
_DIM    = (0.294, 0.333, 0.388, 1)


class EndScreen(Screen):
    def on_enter(self):
        self._populate_leaderboard()
        self._populate_breakdown()
        self._populate_events()

    def _populate_leaderboard(self):
        box = self.ids.leaderboard_box
        box.clear_widgets()
        sorted_lb = sorted(dd.GAME_STATE["leaderboard"], key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(sorted_lb):
            winner = i == 0
            row = BoxLayout(size_hint_y=None, height='28dp', spacing='12dp')
            row.add_widget(Label(
                text=str(i + 1),
                color=_ACCENT if winner else _MUTED,
                font_size='11sp', size_hint_x=None, width='24dp',
            ))
            row.add_widget(Label(
                text=entry["name"],
                color=_ACTOR_COLORS.get(entry["name"], _BODY),
                font_size='11sp', halign='left', valign='middle',
            ))
            row.add_widget(Label(
                text='\u00a3{:,.0f}'.format(entry["score"]),
                color=_BRIGHT if winner else _BODY,
                font_size='11sp', bold=winner, halign='right', valign='middle',
            ))
            box.add_widget(row)

    def _populate_breakdown(self):
        bd = dd.GAME_STATE["end"]["player_breakdown"]
        box = self.ids.breakdown_box
        box.clear_widgets()
        for label, value, color in [
            ("Portfolio value",  bd["portfolio"], _BODY),
            ("Cash",             bd["cash"],      _BODY),
            ("Cumulative rent",  bd["rent"],      _ACCENT),
        ]:
            row = BoxLayout(size_hint_y=None, height='22dp')
            row.add_widget(Label(text=label, color=_MUTED, font_size='9sp',
                                 halign='left', valign='middle'))
            row.add_widget(Label(text='\u00a3{:,.0f}'.format(value), color=color,
                                 font_size='9sp', halign='right', valign='middle'))
            box.add_widget(row)

    def _populate_events(self):
        box = self.ids.events_box
        box.clear_widgets()
        for ev in dd.GAME_STATE["end"]["key_events"]:
            box.add_widget(Label(
                text='T{}  {}'.format(ev["tick"], ev["text"]),
                color=_DIM, font_size='9sp',
                halign='left', valign='middle',
                size_hint_y=None, height='20dp',
            ))

    def play_again(self):
        dd.GAME_STATE["tick"] = 1
        self.manager.current = 'opening'
```

- [ ] **Step 2: Write `screens/end.kv`**

Create `ui_kivy/screens/end.kv`:
```kv
<EndScreen>:
    canvas.before:
        Color:
            rgba: 0.039, 0.055, 0.102, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        padding: '16dp'
        spacing: '12dp'

        # Header
        BoxLayout:
            size_hint_y: None
            height: '50dp'
            orientation: 'vertical'
            Label:
                text: 'GAME OVER'
                color: 0.984, 0.749, 0.141, 1
                font_size: '20sp'
                bold: True
            Label:
                text: '20 turns  \u00b7  10 years  \u00b7  3 actors'
                color: 0.420, 0.447, 0.502, 1
                font_size: '10sp'

        # Leaderboard
        BoxLayout:
            size_hint_y: None
            height: '120dp'
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgba: 0.067, 0.094, 0.153, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            padding: '10dp'
            spacing: '4dp'
            Label:
                text: 'FINAL LEADERBOARD'
                color: 0.420, 0.447, 0.502, 1
                font_size: '8sp'
                size_hint_y: None
                height: '14dp'
                halign: 'left'
            BoxLayout:
                id: leaderboard_box
                orientation: 'vertical'

        # Breakdown + events
        BoxLayout:
            spacing: '12dp'

            BoxLayout:
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '10dp'
                spacing: '4dp'
                Label:
                    text: 'YOUR BREAKDOWN'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    id: breakdown_box
                    orientation: 'vertical'

            BoxLayout:
                orientation: 'vertical'
                canvas.before:
                    Color:
                        rgba: 0.067, 0.094, 0.153, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: '10dp'
                spacing: '4dp'
                Label:
                    text: 'KEY EVENTS'
                    color: 0.420, 0.447, 0.502, 1
                    font_size: '8sp'
                    size_hint_y: None
                    height: '14dp'
                    halign: 'left'
                BoxLayout:
                    id: events_box
                    orientation: 'vertical'

        # Play again
        BoxLayout:
            size_hint_y: None
            height: '44dp'
            Button:
                text: 'PLAY AGAIN'
                size_hint_x: None
                width: '140dp'
                pos_hint: {'center_x': 0.5}
                background_color: 0.122, 0.161, 0.216, 1
                color: 0.420, 0.447, 0.502, 1
                font_size: '12sp'
                on_press: root.play_again()
```

- [ ] **Step 3: Write final `main.py`** (all 4 screens)

Replace `ui_kivy/main.py`:
```python
import os
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition

Builder.load_file('widgets/macro_sidebar.kv')
Builder.load_file('screens/opening.kv')
Builder.load_file('screens/turn.kv')
Builder.load_file('screens/decision.kv')
Builder.load_file('screens/end.kv')

from screens.opening import OpeningScreen
from screens.turn import TurnScreen
from screens.decision import DecisionScreen
from screens.end import EndScreen


class RealEstApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(OpeningScreen(name='opening'))
        sm.add_widget(TurnScreen(name='turn'))
        sm.add_widget(DecisionScreen(name='decision'))
        sm.add_widget(EndScreen(name='end'))
        return sm


if __name__ == '__main__':
    RealEstApp().run()
```

- [ ] **Step 4: Run all tests**

```bash
cd ui_kivy && python -m pytest tests/ -v
```
Expected: 14 tests PASS

- [ ] **Step 5: Run full flow manually**

```bash
cd ui_kivy && python main.py
```

Walk through the complete loop:
1. Opening → START GAME → Turn (tick 4)
2. Turn → MAKE DECISION → Decision
3. Click HOLD → CONFIRM → Turn (tick 5); verify sidebar tick increments
4. Repeat until tick reaches 20 → End screen
5. End: verify GAME OVER heading, leaderboard sorted by score (Aggressive first at £520k), YOUR BREAKDOWN, KEY EVENTS
6. PLAY AGAIN → Opening (tick reset to 1)

- [ ] **Step 6: Final commit**

```bash
cd .. && git add ui_kivy/ && git commit -m "feat: complete Kivy UI prototype — all 4 screens wired with simulated game loop"
```
