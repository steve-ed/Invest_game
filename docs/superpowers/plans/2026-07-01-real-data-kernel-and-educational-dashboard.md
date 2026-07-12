# Real Data Kernel + Educational Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the synthetic scenario/shock system with real UK historical macro data (1983–2024), and add a live browser dashboard (Flask + Chart.js) that displays macro trends and wealth over time with educational callouts.

**Architecture:** At game start the kernel randomly selects a 10-year slice from `data/uk_macro_history.UK_MACRO`. Each tick it reads the next entry directly, setting `MacroState` from real data. Events are inferred by comparing consecutive entries. A Flask server running in a daemon thread writes `turn_state.json` after each tick; the browser polls it and redraws two Chart.js charts.

**Tech Stack:** Python stdlib, Flask (already in requirements or add it), Chart.js via CDN, existing `data/uk_macro_history.py`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `state.py` | Modify | Add `start_year`, `start_half`, `era_label` to `SimulationState` |
| `shocks.py` | Rewrite | Replace `ShockEngine`/`Shock` with `detect_events(prev, curr, tick)` |
| `scenarios.py` | Rewrite | Replace `ScenarioManager` with `label_from_deltas(rate_delta, hpi_delta_pct)` |
| `kernel.py` | Modify | Era selection at init; read UK_MACRO per tick; write `turn_state.json`; start Flask thread |
| `main.py` | Modify | Add `--mode` CLI arg (default `student`) |
| `visualisation/dashboard_server.py` | Create | Flask server: `GET /` → dashboard.html, `GET /state` → turn_state.json |
| `static/dashboard.html` | Create | Browser dashboard: two Chart.js charts + callout banner + sidebar |
| `tests/test_state.py` | Modify | Add tests for new era fields |
| `tests/test_shocks.py` | Rewrite | Tests for `detect_events` |
| `tests/test_scenarios.py` | Rewrite | Tests for `label_from_deltas` |
| `tests/test_kernel.py` | Modify | Update for new kernel signature; test UK_MACRO playback |
| `tests/test_dashboard_server.py` | Create | Tests for Flask `/state` endpoint |

---

## Task 1: Add era fields to SimulationState

**Files:**
- Modify: `state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_state.py`:

```python
def test_simulation_state_has_era_fields():
    s = SimulationState()
    assert s.start_year == 0
    assert s.start_half == 1
    assert s.era_label == ""
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_state.py::test_simulation_state_has_era_fields -v
```

Expected: `AttributeError` — fields don't exist yet.

- [ ] **Step 3: Add fields to SimulationState**

In `state.py`, update `SimulationState` to:

```python
@dataclass
class SimulationState:
    tick: int = 0
    current_scenario: str = "baseline"
    macro: MacroState = field(default_factory=MacroState)
    properties: list = field(default_factory=list)
    actors: dict = field(default_factory=dict)
    macro_history: list = field(default_factory=list)
    last_ai_actions: dict = field(default_factory=dict)
    event_log: list = field(default_factory=list)
    start_year: int = 0
    start_half: int = 1
    era_label: str = ""

    def advance_tick(self):
        self.tick += 1
```

- [ ] **Step 4: Run all state tests**

```
pytest tests/test_state.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: add start_year, start_half, era_label to SimulationState"
```

---

## Task 2: Replace shocks.py with detect_events

**Files:**
- Rewrite: `shocks.py`
- Rewrite: `tests/test_shocks.py`

- [ ] **Step 1: Write failing tests**

Replace the entire contents of `tests/test_shocks.py` with:

```python
from shocks import detect_events

# UK_MACRO tuple format: (year, half, price_index, rate, rent_growth)
ENTRY_A = (1987, 1, 152.0, 8.5, 5.0)
ENTRY_B = (1987, 2, 171.0, 8.5, 5.0)   # big price surge
ENTRY_C = (1989, 2, 213.0, 15.0, 6.0)  # big rate hike
ENTRY_D = (1992, 1, 177.0, 6.0, 3.5)   # big rate cut
ENTRY_E = (1991, 1, 190.0, 12.0, 3.0)  # big price fall from C
ENTRY_F = (1993, 1, 168.0, 6.0, 2.0)   # rent squeeze


def test_no_events_on_first_tick():
    events = detect_events(None, ENTRY_A, tick=1)
    assert events == []


def test_rate_shock_up_fires_when_rate_rises_over_1_5():
    # rate goes from 8.5 to 15.0 — delta = +6.5
    events = detect_events(ENTRY_A, ENTRY_C, tick=5)
    types = [e["type"] for e in events]
    assert "rate_shock_up" in types


def test_rate_shock_down_fires_when_rate_falls_over_1_5():
    # rate goes from 15.0 to 6.0 — delta = -9.0
    events = detect_events(ENTRY_C, ENTRY_D, tick=10)
    types = [e["type"] for e in events]
    assert "rate_shock_down" in types


def test_price_surge_fires_when_hpi_rises_over_8_pct():
    # HPI goes from 152 to 171 — delta = 12.5%
    events = detect_events(ENTRY_A, ENTRY_B, tick=2)
    types = [e["type"] for e in events]
    assert "price_surge" in types


def test_price_crash_fires_when_hpi_falls_over_5_pct():
    # HPI goes from 213 to 190 — delta = -10.8%
    events = detect_events(ENTRY_C, ENTRY_E, tick=6)
    types = [e["type"] for e in events]
    assert "price_crash" in types


def test_rent_squeeze_fires_when_rent_growth_falls_over_1():
    # rent_growth goes from 6.0 to 2.0 — delta = -4.0
    events = detect_events(ENTRY_C, ENTRY_F, tick=8)
    types = [e["type"] for e in events]
    assert "rent_squeeze" in types


def test_event_has_required_fields():
    events = detect_events(ENTRY_A, ENTRY_C, tick=5)
    assert len(events) > 0
    for e in events:
        assert "type" in e
        assert "tick" in e
        assert "detail" in e
        assert "delta" in e
        assert e["tick"] == 5


def test_no_event_on_stable_conditions():
    # tiny changes — nothing should fire
    stable_a = (1995, 1, 181.0, 6.5, 3.5)
    stable_b = (1995, 2, 182.0, 6.5, 3.5)
    events = detect_events(stable_a, stable_b, tick=3)
    assert events == []
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_shocks.py -v
```

Expected: `ImportError` — `detect_events` doesn't exist yet.

- [ ] **Step 3: Rewrite shocks.py**

Replace the entire contents of `shocks.py` with:

```python
# Each rule: (event_type, condition_fn(rate_delta, hpi_delta_pct, rent_delta), detail_str, delta_key)
# rate_delta: percentage points (e.g. +1.5 means rate rose 1.5%)
# hpi_delta_pct: % change in house price index
# rent_delta: percentage points change in annual rent growth rate
_RULES = [
    ("rate_shock_up",   lambda rd, hd, rend: rd > 1.5,           "Mortgages get costlier; prices may fall",      "rate_delta"),
    ("rate_shock_down", lambda rd, hd, rend: rd < -1.5,          "Cheaper borrowing; demand lifts prices",       "rate_delta"),
    ("rate_rise",       lambda rd, hd, rend: 0.5 < rd <= 1.5,    "Borrowing costs increasing",                   "rate_delta"),
    ("rate_cut",        lambda rd, hd, rend: -1.5 <= rd < -0.5,  "Borrowing costs easing",                       "rate_delta"),
    ("price_crash",     lambda rd, hd, rend: hd < -5.0,          "Market correction; portfolio loses value",     "hpi_delta_pct"),
    ("price_surge",     lambda rd, hd, rend: hd > 8.0,           "Boom conditions; hold and ride it",            "hpi_delta_pct"),
    ("rent_surge",      lambda rd, hd, rend: rend > 2.0,         "Income growing; landlords benefit",            "rent_delta"),
    ("rent_squeeze",    lambda rd, hd, rend: rend < -1.0,        "Rental income under pressure",                 "rent_delta"),
]


def detect_events(prev_entry, curr_entry, tick: int) -> list:
    """
    Compare two consecutive UK_MACRO entries and return event dicts for significant changes.

    prev_entry: (year, half, price_index, rate, rent_growth) or None (tick 0 — no events fired)
    curr_entry: (year, half, price_index, rate, rent_growth)
    tick: current simulation tick number (written into each event dict)
    """
    if prev_entry is None:
        return []

    _, _, prev_hpi, prev_rate, prev_rent = prev_entry
    _, _, curr_hpi, curr_rate, curr_rent = curr_entry

    rate_delta = curr_rate - prev_rate
    hpi_delta_pct = (curr_hpi - prev_hpi) / prev_hpi * 100
    rent_delta = curr_rent - prev_rent

    deltas = {"rate_delta": rate_delta, "hpi_delta_pct": hpi_delta_pct, "rent_delta": rent_delta}

    events = []
    for event_type, condition, detail, delta_key in _RULES:
        if condition(rate_delta, hpi_delta_pct, rent_delta):
            events.append({
                "type": event_type,
                "tick": tick,
                "detail": detail,
                "delta": round(deltas[delta_key], 2),
            })
    return events
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_shocks.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite to check nothing broke**

```
pytest --tb=short -q
```

Note: `test_kernel.py` tests that pass `shocks=[Shock(...)]` will fail — that's expected and fixed in Task 4.

- [ ] **Step 6: Commit**

```bash
git add shocks.py tests/test_shocks.py
git commit -m "feat: replace ShockEngine with detect_events using UK_MACRO deltas"
```

---

## Task 3: Simplify scenarios.py to label_from_deltas

**Files:**
- Rewrite: `scenarios.py`
- Rewrite: `tests/test_scenarios.py`

- [ ] **Step 1: Write failing tests**

Replace the entire contents of `tests/test_scenarios.py` with:

```python
from scenarios import label_from_deltas


def test_downturn_when_prices_fall_sharply():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=-4.0) == "downturn"


def test_downturn_when_rate_rises_sharply():
    assert label_from_deltas(rate_delta=2.0, hpi_delta_pct=0.0) == "downturn"


def test_boom_when_prices_rise_fast():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=6.0) == "boom"


def test_baseline_when_stable():
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=1.0) == "baseline"


def test_downturn_takes_priority_over_boom():
    # falling prices beats anything
    assert label_from_deltas(rate_delta=0.0, hpi_delta_pct=-4.0) == "downturn"


def test_returns_string():
    result = label_from_deltas(0.0, 0.0)
    assert isinstance(result, str)
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_scenarios.py -v
```

Expected: `ImportError` — `label_from_deltas` doesn't exist yet.

- [ ] **Step 3: Rewrite scenarios.py**

Replace the entire contents of `scenarios.py` with:

```python
def label_from_deltas(rate_delta: float, hpi_delta_pct: float) -> str:
    """
    Derive a human-readable scenario label from consecutive UK_MACRO entry deltas.

    rate_delta: change in interest rate in percentage points (e.g. +1.5 = rates rose 1.5%)
    hpi_delta_pct: percentage change in house price index (e.g. -5.0 = prices fell 5%)
    """
    if hpi_delta_pct < -3.0 or rate_delta > 1.5:
        return "downturn"
    if hpi_delta_pct > 5.0:
        return "boom"
    return "baseline"
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_scenarios.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scenarios.py tests/test_scenarios.py
git commit -m "feat: replace ScenarioManager with label_from_deltas"
```

---

## Task 4: Wire kernel to UK_MACRO — era selection and per-tick playback

**Files:**
- Modify: `kernel.py`
- Modify: `tests/test_kernel.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_kernel.py` with:

```python
import json
import os
import tempfile
from kernel import SimulationKernel


def test_run_returns_trace_with_correct_tick_count():
    kernel = SimulationKernel(turns=5)
    results = kernel.run()
    assert len(results["trace"]) == 5


def test_state_tick_advances_each_turn():
    kernel = SimulationKernel(turns=3)
    kernel.run()
    assert kernel.state.tick == 3


def test_macro_values_come_from_uk_macro_slice():
    kernel = SimulationKernel(turns=3)
    kernel.run()
    # After run, macro should reflect the 3rd entry of the chosen slice
    # price_index is normalised to 100 at tick 0, so at tick 3 it may differ
    assert kernel.state.macro.price_index > 0


def test_state_has_era_fields_after_init():
    kernel = SimulationKernel(turns=5)
    assert kernel.state.start_year > 0
    assert kernel.state.start_half in (1, 2)
    assert kernel.state.era_label != ""


def test_trace_contains_property_valuation_events():
    kernel = SimulationKernel(turns=2)
    results = kernel.run()
    all_events = [e for tick in results["trace"] for e in tick["events"]]
    valuation_events = [e for e in all_events if e["type"] == "property_valuation"]
    assert len(valuation_events) > 0


def test_leaderboard_present_in_results():
    kernel = SimulationKernel(turns=2)
    results = kernel.run()
    assert "leaderboard" in results
    assert len(results["leaderboard"]) > 0


def test_macro_interest_rate_is_decimal():
    # interest_rate must be stored as decimal (e.g. 0.085 not 8.5)
    kernel = SimulationKernel(turns=2)
    kernel.run()
    assert kernel.state.macro.interest_rate < 1.0


def test_turn_state_json_written(tmp_path, monkeypatch):
    json_path = tmp_path / "turn_state.json"
    monkeypatch.setattr("kernel.TURN_STATE_PATH", str(json_path))
    kernel = SimulationKernel(turns=2)
    kernel.run()
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert "tick" in data
    assert "macro_history" in data
    assert "wealth_history" in data
```

- [ ] **Step 2: Run to confirm failures**

```
pytest tests/test_kernel.py -v
```

Expected: several failures — `era_label` missing, `TURN_STATE_PATH` missing, etc.

- [ ] **Step 3: Rewrite kernel.py**

Replace `kernel.py` with:

```python
import sys
import io
import json
import random
import os
import threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from state import SimulationState, Property, ActorState, MacroState, MacroSnapshot
from shocks import detect_events
from scenarios import label_from_deltas
from actors import ActorManager
from ai import AIController
from narrative.branching import BranchingEngine
from narrative.scenario_events import ScenarioEventEngine
from player.choices import PlayerChoiceEngine
from property_model import PropertyModel
from scoring import ScoringEngine
from ui.event_log_state import EventLogState
from ui.event_log_components import EventLogComponents
from ui.dashboard import show_opening, show_end
from data.uk_macro_history import get_slice, get_start_limits, get_era_label

TURN_STATE_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "turn_state.json")


def _default_properties():
    return [
        Property(id="p01", region="London Kensington",   base_value=500000.0, current_value=500000.0, rent=2500.0),
        Property(id="p02", region="Oxford",              base_value=230000.0, current_value=230000.0, rent=1150.0),
        Property(id="p03", region="Brighton",            base_value=220000.0, current_value=220000.0, rent=1100.0),
        Property(id="p04", region="Sheffield",           base_value=130000.0, current_value=130000.0, rent=650.0),
        Property(id="p05", region="Leicester",           base_value=140000.0, current_value=140000.0, rent=700.0),
        Property(id="p06", region="Bristol",             base_value=260000.0, current_value=260000.0, rent=1300.0),
        Property(id="p07", region="Cambridge",           base_value=250000.0, current_value=250000.0, rent=1250.0),
        Property(id="p08", region="Birmingham",          base_value=200000.0, current_value=200000.0, rent=1000.0),
        Property(id="p09", region="Manchester",          base_value=240000.0, current_value=240000.0, rent=1200.0),
        Property(id="p10", region="Leeds",               base_value=170000.0, current_value=170000.0, rent=850.0),
        Property(id="p11", region="Nottingham",          base_value=155000.0, current_value=155000.0, rent=775.0),
        Property(id="p12", region="Liverpool",           base_value=145000.0, current_value=145000.0, rent=725.0),
        Property(id="p13", region="Cardiff",             base_value=160000.0, current_value=160000.0, rent=800.0),
        Property(id="p14", region="Newcastle",           base_value=120000.0, current_value=120000.0, rent=600.0),
        Property(id="p15", region="Sunderland",          base_value=90000.0,  current_value=90000.0,  rent=540.0),
        Property(id="m1",  region="London Shoreditch",   base_value=420000.0, current_value=420000.0, rent=1470.0),
        Property(id="m2",  region="Bristol Harbourside", base_value=230000.0, current_value=230000.0, rent=1035.0),
        Property(id="m3",  region="Leeds City Centre",   base_value=155000.0, current_value=155000.0, rent=930.0),
        Property(id="m4",  region="Sunderland Dockside", base_value=80000.0,  current_value=80000.0,  rent=560.0),
    ]


def _default_actors():
    return {
        "player": ActorState(id="player", name="Player", cash=200000.0, risk_appetite=0.6,
                             portfolio=["p01", "p02", "p03", "p04", "p05"]),
        "ai1": ActorState(id="ai1", name="Conservative AI", cash=490000.0, risk_appetite=0.3,
                          portfolio=["p06", "p07", "p08"]),
        "ai2": ActorState(id="ai2", name="Aggressive AI", cash=120000.0, risk_appetite=0.9,
                          portfolio=["p09", "p10", "p11", "p12", "p13", "p14", "p15"]),
    }


def _portfolio_value(actor, properties):
    prop_map = {p.id: p for p in properties}
    return sum(prop_map[pid].current_value for pid in actor.portfolio if pid in prop_map)


def _select_era(turns):
    min_year, max_year = get_start_limits(turns)
    start_year = random.randint(min_year, max_year)
    start_half = random.choice([1, 2])
    return start_year, start_half


def _normalize_slice(raw_slice):
    """Normalise price_index so the first entry = 100."""
    base_hpi = raw_slice[0][2]
    return [
        (year, half, price_index / base_hpi * 100, rate, rent_growth)
        for year, half, price_index, rate, rent_growth in raw_slice
    ]


class SimulationKernel:
    def __init__(self, turns=20, mode="student"):
        self.turns = turns
        self.mode = mode

        start_year, start_half = _select_era(turns)
        raw_slice = get_slice(start_year, start_half, turns)
        self.historical_slice = _normalize_slice(raw_slice)
        self.era_label = get_era_label(start_year)

        self.state = SimulationState()
        self.state.properties = _default_properties()
        self.state.actors = _default_actors()
        self.state.start_year = start_year
        self.state.start_half = start_half
        self.state.era_label = self.era_label

        self.actors = ActorManager()
        self.ai = AIController()
        self.branching = BranchingEngine()
        self.scenario_events = ScenarioEventEngine()
        self.player_choices = PlayerChoiceEngine()
        self.property_model = PropertyModel()
        self.scoring = ScoringEngine()
        self.event_log = EventLogState()
        self.renderer = EventLogComponents()

        self._wealth_history = []
        self._macro_history_export = []

    def _apply_macro(self, entry):
        _, _, price_index, rate, rent_growth = entry
        self.state.macro = MacroState(
            price_index=price_index,
            interest_rate=rate / 100.0,
            rent_growth=rent_growth / 100.0,
        )

    def _write_turn_state(self, current_events, is_final=False):
        actors_data = {}
        for actor_id, actor in self.state.actors.items():
            pv = _portfolio_value(actor, self.state.properties)
            actors_data[actor_id] = {
                "name": actor.name,
                "cash": round(actor.cash, 2),
                "portfolio_value": round(pv, 2),
                "total": round(actor.cash + pv, 2),
            }

        x_labels = []
        for i, (year, half, *_) in enumerate(self.historical_slice):
            x_labels.append(f"Y{(i // 2) + 1} H{half}")

        data = {
            "tick": self.state.tick,
            "total_ticks": self.turns,
            "mode": self.mode,
            "scenario": self.state.current_scenario,
            "macro_history": self._macro_history_export,
            "wealth_history": self._wealth_history,
            "current_events": [e for e in current_events
                                if e["type"] in ("rate_shock_up", "rate_shock_down",
                                                  "rate_rise", "rate_cut",
                                                  "price_crash", "price_surge",
                                                  "rent_surge", "rent_squeeze")],
            "actors": actors_data,
            "x_labels": x_labels,
            "era_label": self.era_label if is_final else None,
        }
        os.makedirs(os.path.dirname(TURN_STATE_PATH), exist_ok=True)
        with open(TURN_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def run(self):
        trace = []
        if sys.stdin.isatty():
            show_opening(self.state)

        prev_entry = None

        for i in range(self.turns):
            self.state.advance_tick()
            tick = self.state.tick
            curr_entry = self.historical_slice[i]

            self._apply_macro(curr_entry)

            tick_events = []
            tick_events += detect_events(prev_entry, curr_entry, tick)

            _, _, price_index, rate, rent_growth = curr_entry
            prev_price_index = prev_entry[2] if prev_entry else price_index
            rate_delta = (curr_entry[3] - prev_entry[3]) if prev_entry else 0.0
            hpi_delta_pct = (price_index - prev_price_index) / prev_price_index * 100 if prev_entry else 0.0
            self.state.current_scenario = label_from_deltas(rate_delta, hpi_delta_pct)
            tick_events.append({
                "type": "scenario_advance",
                "tick": tick,
                "scenario": self.state.current_scenario,
                "detail": f"Scenario: {self.state.current_scenario}",
            })

            tick_events += self.actors.step(self.state, tick)

            ai_events = self.ai.step(self.state, tick)
            for event in ai_events:
                self._execute_action(event)
            tick_events += ai_events

            for event in ai_events:
                actor_id = event.get("actor_id")
                action = event.get("action", "hold")
                pid = event.get("property_id")
                if actor_id:
                    self.state.last_ai_actions[actor_id] = (
                        f"bought {pid}" if action == "buy" else
                        f"sold {pid}" if action == "sell" else "hold"
                    )

            player_events = self.player_choices.step(self.state, tick)
            for event in player_events:
                self._execute_action(event)
            tick_events += player_events

            tick_events += self.branching.step(self.state, tick)
            tick_events += self.scenario_events.step(self.state, tick)
            tick_events += self.property_model.update(self.state)

            self.event_log.append_events(tick_events)
            self.state.event_log.extend(tick_events)
            self.state.macro_history.append(MacroSnapshot(
                tick=tick,
                scenario=self.state.current_scenario,
                price_index=self.state.macro.price_index,
                interest_rate=self.state.macro.interest_rate,
                rent_growth=self.state.macro.rent_growth,
                events=[e for e in tick_events if e["type"] in
                        ("rate_shock_up", "rate_shock_down", "price_crash",
                         "price_surge", "rent_surge", "rent_squeeze")],
            ))

            self._macro_history_export.append({
                "tick": tick,
                "price_index": round(self.state.macro.price_index, 2),
                "rate": round(rate, 2),
                "rent_growth": round(rent_growth, 2),
            })
            wealth_snap = {"tick": tick}
            for actor_id, actor in self.state.actors.items():
                wealth_snap[actor_id] = round(actor.cash + _portfolio_value(actor, self.state.properties), 2)
            self._wealth_history.append(wealth_snap)

            is_final = (i == self.turns - 1)
            self._write_turn_state(tick_events, is_final=is_final)
            trace.append({"tick": tick, "events": tick_events})

            prev_entry = curr_entry

        leaderboard = self.scoring.leaderboard(self.state)
        if sys.stdin.isatty():
            show_end(self.state, leaderboard)
        return {"trace": trace, "leaderboard": leaderboard}

    def _execute_action(self, event):
        actor_id = event.get("actor_id")
        action = event.get("action")
        property_id = event.get("property_id")
        if not actor_id or action == "hold" or not property_id:
            return
        actor = self.state.actors.get(actor_id)
        if not actor:
            return
        prop_map = {p.id: p for p in self.state.properties}
        owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}
        prop = prop_map.get(property_id)
        if not prop:
            return
        if action == "sell" and property_id in actor.portfolio:
            actor.cash += prop.current_value
            actor.portfolio.remove(property_id)
        elif action == "buy" and property_id not in owned_all and actor.cash >= prop.current_value:
            actor.cash -= prop.current_value
            actor.portfolio.append(property_id)
```

- [ ] **Step 4: Run kernel tests**

```
pytest tests/test_kernel.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```
pytest --tb=short -q
```

Expected: all pass except possibly `test_narrative.py`, `test_ai.py` (check — these don't depend on ShockEngine/ScenarioManager directly and should pass).

- [ ] **Step 6: Run the game end-to-end**

```
python main.py
```

Expected: game runs to completion, prints leaderboard, writes `visualisation/turn_state.json`.

- [ ] **Step 7: Commit**

```bash
git add kernel.py tests/test_kernel.py
git commit -m "feat: kernel plays back real UK_MACRO historical slice"
```

---

## Task 5: Flask dashboard server

**Files:**
- Create: `visualisation/dashboard_server.py`
- Create: `tests/test_dashboard_server.py`

- [ ] **Step 1: Ensure Flask is available**

```
pip show flask
```

If not installed:
```
pip install flask && pip freeze | grep -i flask >> requirements.txt
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_dashboard_server.py`:

```python
import json
import os
import tempfile
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    state_path = tmp_path / "turn_state.json"
    state_path.write_text(json.dumps({
        "tick": 3,
        "total_ticks": 20,
        "mode": "student",
        "macro_history": [],
        "wealth_history": [],
        "current_events": [],
        "actors": {},
        "x_labels": [],
        "era_label": None,
        "scenario": "baseline",
    }))
    monkeypatch.setenv("TURN_STATE_PATH", str(state_path))
    from visualisation.dashboard_server import create_app
    app = create_app(str(state_path))
    app.config["TESTING"] = True
    return app.test_client()


def test_state_endpoint_returns_json(client):
    resp = client.get("/state")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["tick"] == 3


def test_state_endpoint_has_cors_header(client):
    resp = client.get("/state")
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower() or b"<!doctype" in resp.data.lower()
```

- [ ] **Step 3: Run to confirm failures**

```
pytest tests/test_dashboard_server.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 4: Create visualisation/dashboard_server.py**

```python
import json
import os
import socket
import threading
from flask import Flask, Response, send_file

_DEFAULT_STATE_PATH = os.path.join(os.path.dirname(__file__), "turn_state.json")


def create_app(state_path=None):
    if state_path is None:
        state_path = _DEFAULT_STATE_PATH

    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    app = Flask(__name__, static_folder=static_dir)

    @app.route("/state")
    def state():
        try:
            with open(state_path, encoding="utf-8") as f:
                data = f.read()
        except FileNotFoundError:
            data = "{}"
        return Response(data, mimetype="application/json",
                        headers={"Access-Control-Allow-Origin": "*"})

    @app.route("/")
    def index():
        dashboard = os.path.join(static_dir, "dashboard.html")
        return send_file(dashboard)

    return app


def _find_port(start=5050, end=5059):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def start_server(state_path=None):
    app = create_app(state_path)
    port = _find_port()
    print(f"Dashboard: http://localhost:{port}", flush=True)
    t = threading.Thread(target=lambda: app.run(port=port, use_reloader=False), daemon=True)
    t.start()
    return port
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_dashboard_server.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add visualisation/dashboard_server.py tests/test_dashboard_server.py
git commit -m "feat: Flask dashboard server serving turn_state.json"
```

---

## Task 6: Browser dashboard (static/dashboard.html)

**Files:**
- Create: `static/dashboard.html`

No automated tests for the browser — verified by running the game and opening the URL.

- [ ] **Step 1: Create static/ directory and dashboard.html**

Create `static/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RealEstGame Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f1923; color: #e0e0e0; font-size: 13px; }

  .top-bar {
    background: #1a2733; border-bottom: 2px solid #209dd7;
    padding: 10px 20px; display: flex; align-items: center; justify-content: space-between;
  }
  .top-bar h1 { font-size: 16px; color: #ecad0a; letter-spacing: 1px; }
  .badge {
    border-radius: 4px; padding: 4px 12px; font-size: 12px;
    background: #032147; border: 1px solid #209dd7; color: #209dd7;
  }
  .badge.scenario { background: #1e3a1e; border-color: #4caf50; color: #4caf50; }

  .layout {
    display: grid; grid-template-columns: 1fr 280px; grid-template-rows: auto 1fr 1fr;
    gap: 12px; padding: 12px; height: calc(100vh - 49px);
  }

  .callout {
    grid-column: 1 / -1; background: #1a2a1a; border-left: 4px solid #ecad0a;
    border-radius: 4px; padding: 10px 16px; display: none; align-items: flex-start; gap: 12px;
  }
  .callout.visible { display: flex; }
  .callout-icon { font-size: 18px; flex-shrink: 0; }
  .callout-title { color: #ecad0a; font-weight: 600; font-size: 13px; margin-bottom: 3px; }
  .callout-body { color: #b0c0b0; font-size: 12px; line-height: 1.5; }

  .chart-panel {
    background: #1a2733; border: 1px solid #2a3f50; border-radius: 6px;
    padding: 14px 16px; display: flex; flex-direction: column; min-height: 0;
  }
  .chart-panel h3 {
    font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    color: #888; margin-bottom: 8px; flex-shrink: 0;
  }
  .chart-wrap { flex: 1; position: relative; min-height: 0; }

  .sidebar { grid-row: 2 / 4; grid-column: 2; display: flex; flex-direction: column; gap: 12px; }
  .panel {
    background: #1a2733; border: 1px solid #2a3f50; border-radius: 6px; padding: 12px 14px;
  }
  .panel h3 { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 8px; }

  .bar-row { margin-bottom: 10px; }
  .bar-label { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; color: #ccc; }
  .bar-label span:last-child { color: #888; }
  .bar-track { height: 8px; background: #0f1923; border-radius: 3px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s; }

  .event-item { font-size: 11px; color: #aaa; padding: 6px 0; border-bottom: 1px solid #2a3f50; line-height: 1.4; }
  .event-item:last-child { border-bottom: none; }
  .event-tag {
    display: inline-block; font-size: 10px; padding: 1px 5px;
    border-radius: 3px; margin-right: 4px; font-weight: 600;
  }
  .tag-shock { background: #4a1a1a; color: #f44336; }
  .tag-boom  { background: #1a3a1a; color: #4caf50; }
  .tag-rent  { background: #3a2a1a; color: #ecad0a; }
  .tag-info  { background: #1a2a4a; color: #209dd7; }

  #era-banner {
    display: none; grid-column: 1 / -1; background: #2a1a00;
    border: 2px solid #ecad0a; border-radius: 6px; padding: 16px 20px; text-align: center;
  }
  #era-banner h2 { color: #ecad0a; margin-bottom: 6px; }
  #era-banner p { color: #b0c0b0; font-size: 12px; }
</style>
</head>
<body>

<div class="top-bar">
  <h1>REALESTGAME · Student Mode</h1>
  <div style="display:flex;gap:10px;align-items:center;">
    <div class="badge scenario" id="scenario-badge">Baseline</div>
    <div class="badge" id="turn-badge">—</div>
  </div>
</div>

<div class="layout">
  <div class="callout" id="callout">
    <div class="callout-icon" id="callout-icon">📢</div>
    <div>
      <div class="callout-title" id="callout-title"></div>
      <div class="callout-body" id="callout-body"></div>
    </div>
  </div>

  <div class="chart-panel">
    <h3>Macro Economy — Interest Rate · Price Index · Rent Growth</h3>
    <div class="chart-wrap"><canvas id="macro-chart"></canvas></div>
  </div>

  <div class="chart-panel">
    <h3>Portfolio Wealth — All Actors</h3>
    <div class="chart-wrap"><canvas id="wealth-chart"></canvas></div>
  </div>

  <div class="sidebar">
    <div class="panel">
      <h3>Current Wealth</h3>
      <div id="wealth-bars"></div>
    </div>
    <div class="panel" style="flex:1;overflow:auto;">
      <h3>What just happened</h3>
      <div id="event-feed"></div>
    </div>
  </div>

  <div id="era-banner">
    <h2 id="era-title"></h2>
    <p id="era-sub"></p>
  </div>
</div>

<script>
const ACTOR_COLORS = { player: "#753991", ai1: "#209dd7", ai2: "#ecad0a" };
const ACTOR_NAMES  = { player: "You", ai1: "Conservative AI", ai2: "Aggressive AI" };

const CALLOUT_PRIORITY = [
  "price_crash", "rate_shock_up", "price_surge", "rate_shock_down",
  "rent_surge", "rent_squeeze", "rate_rise", "rate_cut"
];
const CALLOUT_ICONS = {
  price_crash: "📉", rate_shock_up: "⚡", price_surge: "🚀",
  rate_shock_down: "💸", rent_surge: "💰", rent_squeeze: "⚠️",
  rate_rise: "📈", rate_cut: "✂️"
};
const EVENT_TAG_CLASS = {
  price_crash: "tag-shock", rate_shock_up: "tag-shock",
  price_surge: "tag-boom",  rate_shock_down: "tag-boom",
  rent_surge:  "tag-rent",  rent_squeeze: "tag-shock",
  rate_rise:   "tag-info",  rate_cut: "tag-info",
};

const chartDefaults = {
  responsive: true, maintainAspectRatio: false,
  animation: { duration: 400 },
  plugins: { legend: { labels: { color: "#aaa", boxWidth: 12, font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: "#555", maxTicksLimit: 10, font: { size: 10 } }, grid: { color: "#1e2f3a" } },
    y: { ticks: { color: "#555", font: { size: 10 } }, grid: { color: "#1e2f3a" } },
  },
};

function makeAnnotations(macroHistory) {
  const anns = {};
  macroHistory.forEach((m, i) => {
    const prev = macroHistory[i - 1];
    if (!prev) return;
    const rateDelta = m.rate - prev.rate;
    const hpiDelta  = (m.price_index - prev.price_index) / prev.price_index * 100;
    if (Math.abs(rateDelta) > 1.5 || Math.abs(hpiDelta) > 8) {
      anns[`shock_${i}`] = {
        type: "line", scaleID: "x", value: i,
        borderColor: "rgba(255,255,255,0.2)", borderWidth: 1, borderDash: [4, 4],
      };
    }
  });
  return anns;
}

let macroChart = null;
let wealthChart = null;

function buildMacroChart(labels, macro) {
  const ctx = document.getElementById("macro-chart").getContext("2d");
  const anns = makeAnnotations(macro);
  if (macroChart) { macroChart.destroy(); }
  macroChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Price Index", data: macro.map(m => m.price_index), borderColor: "#ecad0a", borderWidth: 2, pointRadius: 0, tension: 0.3 },
        { label: "Interest Rate %", data: macro.map(m => m.rate), borderColor: "#f44336", borderWidth: 2, pointRadius: 0, tension: 0.3 },
        { label: "Rent Growth %", data: macro.map(m => m.rent_growth), borderColor: "#4caf50", borderWidth: 2, pointRadius: 0, tension: 0.3 },
      ],
    },
    options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, annotation: { annotations: anns } } },
  });
}

function buildWealthChart(labels, wealthHistory) {
  const ctx = document.getElementById("wealth-chart").getContext("2d");
  const actorIds = Object.keys(ACTOR_COLORS);
  if (wealthChart) { wealthChart.destroy(); }
  wealthChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: actorIds.map(id => ({
        label: ACTOR_NAMES[id] || id,
        data: wealthHistory.map(w => w[id] ?? null),
        borderColor: ACTOR_COLORS[id],
        borderWidth: id === "player" ? 2.5 : 2,
        pointRadius: 0,
        tension: 0.3,
      })),
    },
    options: { ...chartDefaults },
  });
}

function updateWealthBars(actors) {
  const el = document.getElementById("wealth-bars");
  const entries = Object.entries(actors);
  const maxTotal = Math.max(...entries.map(([, a]) => a.total));
  el.innerHTML = entries.map(([id, a]) => `
    <div class="bar-row">
      <div class="bar-label"><span>${ACTOR_NAMES[id] || id}</span><span>£${Math.round(a.total / 1000)}k</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${(a.total/maxTotal*100).toFixed(1)}%;background:${ACTOR_COLORS[id]};"></div></div>
    </div>`).join("");
}

function updateCallout(currentEvents) {
  const el = document.getElementById("callout");
  const type = CALLOUT_PRIORITY.find(t => currentEvents.some(e => e.type === t));
  if (!type) { el.classList.remove("visible"); return; }
  const ev = currentEvents.find(e => e.type === type);
  document.getElementById("callout-icon").textContent  = CALLOUT_ICONS[type] || "📢";
  document.getElementById("callout-title").textContent = type.replace(/_/g, " ").toUpperCase();
  document.getElementById("callout-body").textContent  = ev.detail;
  el.classList.add("visible");
}

function updateEventFeed(currentEvents) {
  const el = document.getElementById("event-feed");
  if (!currentEvents.length) { el.innerHTML = '<div class="event-item" style="color:#555">Quiet turn — no major events</div>'; return; }
  el.innerHTML = currentEvents.slice(0, 6).map(e => {
    const cls = EVENT_TAG_CLASS[e.type] || "tag-info";
    const label = e.type.replace(/_/g, " ");
    return `<div class="event-item"><span class="event-tag ${cls}">${label}</span>${e.detail}</div>`;
  }).join("");
}

function showEraBanner(eraLabel) {
  const banner = document.getElementById("era-banner");
  banner.style.display = "block";
  document.getElementById("era-title").textContent = `You played: ${eraLabel}`;
  document.getElementById("era-sub").textContent = "Era revealed — see leaderboard in terminal";
}

async function poll() {
  try {
    const resp = await fetch("/state?" + Date.now());
    if (!resp.ok) return;
    const d = await resp.json();

    document.getElementById("turn-badge").textContent =
      `Turn ${d.tick} / ${d.total_ticks}`;
    const sc = d.scenario || "baseline";
    const scenarioBadge = document.getElementById("scenario-badge");
    scenarioBadge.textContent = sc.charAt(0).toUpperCase() + sc.slice(1);
    scenarioBadge.style.background = sc === "downturn" ? "#3a1a1a" : sc === "boom" ? "#1a3a1a" : "#1e3a1e";
    scenarioBadge.style.borderColor = sc === "downturn" ? "#f44336" : sc === "boom" ? "#ecad0a" : "#4caf50";
    scenarioBadge.style.color       = sc === "downturn" ? "#f44336" : sc === "boom" ? "#ecad0a" : "#4caf50";

    const labels = d.x_labels || d.macro_history.map((_, i) => `T${i+1}`);
    if (d.macro_history.length) buildMacroChart(labels, d.macro_history);
    if (d.wealth_history.length) buildWealthChart(labels, d.wealth_history);
    if (d.actors && Object.keys(d.actors).length) updateWealthBars(d.actors);
    updateCallout(d.current_events || []);
    updateEventFeed(d.current_events || []);

    if (d.era_label) showEraBanner(d.era_label);
  } catch (e) { /* server not ready yet */ }
}

setInterval(poll, 1500);
poll();
</script>
</body>
</html>
```

- [ ] **Step 2: Verify static/ directory created**

```
ls static/dashboard.html
```

- [ ] **Step 3: Commit**

```bash
git add static/dashboard.html
git commit -m "feat: browser dashboard with Chart.js macro + wealth charts"
```

---

## Task 7: Wire dashboard server into kernel and add --mode flag to main.py

**Files:**
- Modify: `kernel.py` (add `start_server()` call in `__init__`)
- Modify: `main.py` (add `--mode` arg)

- [ ] **Step 1: Add server start to SimulationKernel.__init__**

In `kernel.py`, add to the imports at the top:

```python
from visualisation.dashboard_server import start_server
```

Add at the end of `SimulationKernel.__init__`, after `self.event_log = EventLogState()`:

```python
        start_server(TURN_STATE_PATH)
```

- [ ] **Step 2: Update main.py**

Replace `main.py` with:

```python
import sys
import io
import argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from kernel import SimulationKernel
from visualisation.shock_timeline import plot_shock_timeline
from visualisation.scenario_transitions import plot_scenario_transitions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["student", "expert"], default="student")
    args = parser.parse_args()

    kernel = SimulationKernel(turns=20, mode=args.mode)
    results = kernel.run()

    trace = results["trace"]
    leaderboard = results["leaderboard"]

    plot_shock_timeline(trace)
    plot_scenario_transitions(trace)

    print("\n=== LEADERBOARD ===")
    for rank, entry in enumerate(leaderboard, start=1):
        print(
            f"  {rank}. {entry['name']:<20} "
            f"Score: £{entry['final_score']:>12,.0f}  "
            f"(Portfolio: £{entry['portfolio_value']:>10,.0f}  "
            f"Cash: £{entry['cash']:>10,.0f})"
        )

    print(f"\nEra played: {kernel.era_label}")
    print("\nSimulation complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run end-to-end**

```
python main.py --mode student
```

Expected output includes:
- `Dashboard: http://localhost:505X` printed at start
- Game runs 20 turns
- Leaderboard printed
- `Era played: <name>` printed at end

Open `http://localhost:505X` in browser while the game is running and confirm:
- Two charts populate each turn
- Callout banner appears on shock events
- Era banner appears at the end

- [ ] **Step 4: Run full test suite**

```
pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add kernel.py main.py
git commit -m "feat: start dashboard server at game start, add --mode flag"
```

---

## Self-Review

**Spec coverage:**
- [x] Era selection at game start — Task 4
- [x] Real UK_MACRO playback per tick — Task 4
- [x] `start_year`, `start_half`, `era_label` on SimulationState — Task 1
- [x] `detect_events` replacing ShockEngine — Task 2
- [x] `label_from_deltas` replacing ScenarioManager — Task 3
- [x] Flask server daemon thread, port auto-discovery 5050–5059 — Task 5
- [x] `turn_state.json` written each tick — Task 4
- [x] Browser polls `/state` every 1.5s — Task 6
- [x] Macro history chart (rate/HPI/rent) — Task 6
- [x] Wealth chart (all actors) — Task 6
- [x] Callout banner from current events — Task 6
- [x] `era_label` hidden until final tick — Tasks 4 + 6
- [x] `--mode` CLI arg — Task 7
- [x] price_index normalised to 100 at game start — Task 4
- [x] interest_rate and rent_growth converted from % to decimal for MacroState — Task 4

**Gaps:** None found.
