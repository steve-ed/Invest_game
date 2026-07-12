# UI Readability & AI Panel Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all game UI text legible and show rich per-turn AI decisions on the Turn screen.

**Architecture:** Two independent changes — (1) font/layout scaling across `.kv` files and Python label creation, (2) data model extension in `dummy_data.py` + AI panel rebuild in `turn.py`/`turn.kv`. No new files needed.

**Tech Stack:** Python 3, Kivy 2.3, `.kv` layout language, pytest (headless data-layer tests only — Kivy widgets cannot be tested headlessly).

---

### Task 1: Extend AI dummy data with `last_property` and `rationale`

**Files:**
- Modify: `ui_kivy/dummy_data.py`
- Test: `ui_kivy/tests/test_dummy_data.py`

- [ ] **Step 1: Write the failing test**

Add to `ui_kivy/tests/test_dummy_data.py`:

```python
def test_ai_entries_have_required_fields():
    for ai in GAME_STATE["ai"]:
        assert "last_property" in ai, f"{ai['name']} missing last_property"
        assert "rationale" in ai, f"{ai['name']} missing rationale"
```

- [ ] **Step 2: Run test to verify it fails**

Run from `ui_kivy/`:
```bash
python -m pytest tests/test_dummy_data.py::test_ai_entries_have_required_fields -v
```
Expected: FAIL — `AssertionError: Conservative missing last_property`

- [ ] **Step 3: Add fields to GAME_STATE ai entries in `dummy_data.py`**

Replace the `"ai"` list in `GAME_STATE` (lines 47–50):

```python
    "ai": [
        {
            "name": "Conservative",
            "cash": 30000,
            "portfolio_value": 410000,
            "props": 2,
            "last_action": "hold",
            "last_property": None,
            "rationale": "waiting for rate cut",
        },
        {
            "name": "Aggressive",
            "cash": 15000,
            "portfolio_value": 520000,
            "props": 4,
            "last_action": "buy",
            "last_property": "P-003",
            "rationale": "chasing yield in North",
        },
    ],
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_dummy_data.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add ui_kivy/dummy_data.py ui_kivy/tests/test_dummy_data.py
git commit -m "feat: add last_property and rationale fields to AI dummy data"
```

---

### Task 2: Scale up MacroSidebar fonts and width

**Files:**
- Modify: `ui_kivy/widgets/macro_sidebar.kv`

No automated test possible for `.kv` visual changes — verify by running the app.

- [ ] **Step 1: Widen the sidebar and scale all font sizes**

Replace the entire contents of `ui_kivy/widgets/macro_sidebar.kv`:

```kv
<MacroSidebar>:
    orientation: 'vertical'
    size_hint_x: None
    width: '130dp'
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
        height: '72dp'
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
            font_size: '11sp'
            size_hint_y: None
            height: '16dp'
        Label:
            text: str(root.tick)
            color: 0, 1, 0.533, 1
            font_size: '28sp'
            bold: True
        Label:
            text: 'of ' + str(root.total_ticks)
            color: 0.420, 0.447, 0.502, 1
            font_size: '11sp'
            size_hint_y: None
            height: '16dp'

    # Macro panel
    BoxLayout:
        size_hint_y: None
        height: '150dp'
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
            font_size: '13sp'
            size_hint_y: None
            height: '20dp'
        Label:
            text: 'Px'
            color: 0.420, 0.447, 0.502, 1
            font_size: '11sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: '{:.1f} {}'.format(root.price_index, '\u2191' if root.price_trend == 'up' else ('\u2193' if root.price_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.price_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.price_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '14sp'
            bold: True
            size_hint_y: None
            height: '18dp'
        Label:
            text: 'Rate'
            color: 0.420, 0.447, 0.502, 1
            font_size: '11sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: '{:.1f}% {}'.format(root.rate, '\u2191' if root.rate_trend == 'up' else ('\u2193' if root.rate_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.rate_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.rate_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '14sp'
            bold: True
            size_hint_y: None
            height: '18dp'
        Label:
            text: 'Rent'
            color: 0.420, 0.447, 0.502, 1
            font_size: '11sp'
            size_hint_y: None
            height: '14dp'
        Label:
            text: '{:.1f}% {}'.format(root.rent_growth, '\u2191' if root.rent_trend == 'up' else ('\u2193' if root.rent_trend == 'down' else '\u2192'))
            color: (0, 1, 0.533, 1) if root.rent_trend == 'up' else ((0.973, 0.443, 0.443, 1) if root.rent_trend == 'down' else (0.420, 0.447, 0.502, 1))
            font_size: '14sp'
            bold: True
            size_hint_y: None
            height: '18dp'

    # Rank/score panel
    BoxLayout:
        size_hint_y: None
        height: '72dp'
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
            font_size: '11sp'
            size_hint_y: None
            height: '16dp'
        Label:
            text: '#' + str(root.rank)
            color: 0, 1, 0.533, 1
            font_size: '22sp'
            bold: True
        Label:
            text: '\u00a3{:,.0f}'.format(root.score)
            color: 0.976, 0.980, 0.984, 1
            font_size: '13sp'
            size_hint_y: None
            height: '18dp'

    # Cash panel — Decision screen only
    BoxLayout:
        size_hint_y: None
        height: '48dp' if root.show_cash else '0dp'
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
            font_size: '11sp'
            size_hint_y: None
            height: '16dp'
        Label:
            text: '\u00a3{:,.0f}'.format(root.cash)
            color: 0, 1, 0.533, 1
            font_size: '13sp'
            bold: True

    Widget:
```

- [ ] **Step 2: Run the app and verify sidebar is readable**

```bash
cd ui_kivy && python main.py
```
Expected: sidebar wider, all text clearly legible, scenario/tick/rank/macro values all visible without squinting.

- [ ] **Step 3: Commit**

```bash
git add ui_kivy/widgets/macro_sidebar.kv
git commit -m "feat: scale up MacroSidebar fonts and widen to 130dp"
```

---

### Task 3: Scale up Turn screen section labels and portfolio/news rows

**Files:**
- Modify: `ui_kivy/screens/turn.kv`
- Modify: `ui_kivy/screens/turn.py`

- [ ] **Step 1: Update section label font sizes in `turn.kv`**

In `ui_kivy/screens/turn.kv`, change every `font_size: '8sp'` label that reads `YOUR PORTFOLIO`, `AI POSITIONS`, or `NEWS` to `'12sp'`. Also update the portfolio value and cash label font sizes:

Replace the portfolio panel section (lines 23–64) with:

```kv
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
                font_size: '12sp'
                size_hint_y: None
                height: '18dp'
                halign: 'left'
            BoxLayout:
                size_hint_y: None
                height: '28dp'
                Label:
                    id: portfolio_value_label
                    text: '\u00a30'
                    color: 0, 1, 0.533, 1
                    font_size: '18sp'
                    bold: True
                    halign: 'left'
                Label:
                    id: cash_label
                    text: 'cash \u00a30'
                    color: 0.294, 0.333, 0.388, 1
                    font_size: '12sp'
                    halign: 'right'
            GridLayout:
                id: portfolio_grid
                cols: 5
                spacing: '4dp'
                size_hint_y: None
                height: self.minimum_height
                row_default_height: '24dp'
```

Replace the AI panel section (lines 66–91) with:

```kv
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
                font_size: '12sp'
                size_hint_y: None
                height: '18dp'
                halign: 'left'
            BoxLayout:
                id: ai_box
                orientation: 'vertical'
                spacing: '6dp'
```

Replace the news panel section (lines 93–115) with:

```kv
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
                font_size: '12sp'
                size_hint_y: None
                height: '18dp'
                halign: 'left'
            BoxLayout:
                id: news_box
                orientation: 'vertical'
```

- [ ] **Step 2: Scale portfolio grid and news rows in `turn.py`**

In `ui_kivy/screens/turn.py`, update `_populate_portfolio`, `_populate_ai`, and `_populate_news`:

```python
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
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
_BUY    = (0, 1, 0.533, 1)
_SELL   = (0.973, 0.443, 0.443, 1)


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
                grid.add_widget(Label(text=text, color=color, font_size='12sp',
                                      halign=align, valign='middle'))

    def _populate_ai(self):
        box = self.ids.ai_box
        box.clear_widgets()
        for ai in dd.GAME_STATE["ai"]:
            name_color = _AI_COLORS.get(ai["name"], _BODY)
            action = ai["last_action"]
            prop = ai.get("last_property")
            rationale = ai.get("rationale", "")

            if action == "buy" and prop:
                action_text = "bought {}".format(prop)
                action_color = _BUY
            elif action == "sell" and prop:
                action_text = "sold {}".format(prop)
                action_color = _SELL
            else:
                action_text = "held"
                action_color = _MUTED

            detail = "\u2192 {}".format(action_text)
            if rationale:
                detail += "  \u00b7  {}".format(rationale)

            block = BoxLayout(orientation='vertical', size_hint_y=None, height='44dp')

            # Line 1: name (strategy color) + portfolio summary (muted)
            line1 = BoxLayout(orientation='horizontal')
            line1.add_widget(Label(
                text=ai["name"], color=name_color, font_size='12sp',
                halign='left', valign='middle', size_hint_x=0.35,
            ))
            line1.add_widget(Label(
                text="\u00a3{:,.0f}   {} props".format(ai["portfolio_value"], ai["props"]),
                color=_BODY, font_size='12sp',
                halign='left', valign='middle', size_hint_x=0.65,
            ))
            block.add_widget(line1)

            # Line 2: action verb (colored) + rationale (dim)
            line2 = BoxLayout(orientation='horizontal')
            verb = "\u2192 {}".format(action_text)
            line2.add_widget(Label(
                text=verb, color=action_color, font_size='11sp',
                halign='left', valign='middle', size_hint_x=0.4,
            ))
            if rationale:
                line2.add_widget(Label(
                    text="\u00b7  {}".format(rationale), color=_DIM, font_size='11sp',
                    halign='left', valign='middle', size_hint_x=0.6,
                ))
            block.add_widget(line2)
            box.add_widget(block)

    def _populate_news(self):
        box = self.ids.news_box
        box.clear_widgets()
        for item in dd.GAME_STATE["news"][-2:]:
            box.add_widget(Label(text=item, color=_DIM, font_size='12sp',
                                 halign='left', valign='middle',
                                 size_hint_y=None, height='22dp'))
```

- [ ] **Step 3: Run the app and verify Turn screen**

```bash
cd ui_kivy && python main.py
```
Expected: Turn screen shows readable section labels, portfolio rows legible, AI panel shows two lines per AI (name+value+props on line 1, action+rationale on line 2 with color coding), news items readable.

- [ ] **Step 4: Commit**

```bash
git add ui_kivy/screens/turn.kv ui_kivy/screens/turn.py
git commit -m "feat: scale up Turn screen fonts and enrich AI panel with action detail"
```

---

### Task 4: Scale up Decision screen fonts

**Files:**
- Modify: `ui_kivy/screens/decision.kv`
- Modify: `ui_kivy/screens/decision.py`

- [ ] **Step 1: Update section labels and action button font sizes in `decision.kv`**

Replace the entire contents of `ui_kivy/screens/decision.kv`:

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
                    font_size: '12sp'
                    size_hint_y: None
                    height: '18dp'
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
                    font_size: '12sp'
                    size_hint_y: None
                    height: '18dp'
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
                        font_size: '18sp'
                        bold: True
                        on_press: root.select_action('buy')
                    Button:
                        id: btn_hold
                        text: 'HOLD'
                        background_color: 0.122, 0.161, 0.216, 1
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '18sp'
                        on_press: root.select_action('hold')
                    Button:
                        id: btn_sell
                        text: 'SELL'
                        background_color: 0.122, 0.161, 0.216, 1
                        color: 0.420, 0.447, 0.502, 1
                        font_size: '18sp'
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

- [ ] **Step 2: Update market property row font size and height in `decision.py`**

In `ui_kivy/screens/decision.py`, change the `btn` construction in `_populate_market` — update `font_size` and `height`:

```python
            btn = Button(
                text=label, color=color, font_size='12sp',
                halign='left', valign='middle',
                size_hint_y=None, height='36dp',
                background_color=(0, 0, 0, 0),
            )
```

- [ ] **Step 3: Run the app and verify Decision screen**

```bash
cd ui_kivy && python main.py
```
Navigate to the Decision screen via "MAKE DECISION →". Expected: property list rows are taller and readable, section labels are larger, BUY/HOLD/SELL buttons have larger text.

- [ ] **Step 4: Run all tests**

```bash
cd ui_kivy && python -m pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui_kivy/screens/decision.kv ui_kivy/screens/decision.py
git commit -m "feat: scale up Decision screen fonts"
```
