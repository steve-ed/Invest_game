# RealEstGame Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a fully runnable turn-based property investment simulation with real macro state, shocks, scenarios, AI decisions, scoring, and matplotlib visualisation.

**Architecture:** `SimulationState` is the single mutable object passed by reference through every system each tick. Each system reads from state, mutates it where appropriate, and returns a list of event dicts that accumulate in the event log. `SimulationKernel` orchestrates phase order.

**Tech Stack:** Python 3.13, dataclasses, pytest, matplotlib, numpy (all available in venv except pytest).

---

## File Map

| File | Role | Status |
|---|---|---|
| `state.py` | Dataclasses for MacroState, Property, ActorState, SimulationState | rewrite |
| `shocks.py` | Shock dataclass + ShockEngine (mutates state.macro) | rewrite |
| `scenarios.py` | Scenario configs + ScenarioManager (applies drift, handles transitions) | rewrite |
| `property_model.py` | PropertyModel.update() — recomputes values and rents | rewrite |
| `actors.py` | ActorManager — applies cash interest update per tick | rewrite |
| `ai.py` | AIController — decision tree per AI actor | rewrite |
| `narrative/branching.py` | BranchingEngine — stress vs stable branch | rewrite |
| `narrative/scenario_events.py` | ScenarioEventEngine — flavour text per scenario | rewrite |
| `scoring.py` | ScoringEngine — per-actor score computation | create |
| `kernel.py` | SimulationKernel — phase orchestration, wired correctly | rewrite |
| `visualisation/shock_timeline.py` | Plot shock events across ticks | create |
| `visualisation/scenario_transitions.py` | Plot scenario transitions across ticks | create (move from root) |
| `scenario_transitions.py` (root) | Remove — visualisation content will move to visualisation/ | delete |
| `player/choices.py` | PlayerChoiceEngine — stub returning hold action | keep/extend |
| `ui/event_log_state.py` | EventLogState — accumulates events | keep |
| `ui/event_log_schema.py` | EventLogSchema — field definitions | keep |
| `ui/event_log_components.py` | EventLogComponents — render helper | keep |
| `tests/` | All test files | create |

---

## Task 1: Install pytest and create test directory

**Files:**
- Create: `tests/__init__.py`
- Create: `requirements.txt`

- [ ] **Step 1: Install pytest into the venv**

```bash
venv/Scripts/pip install pytest
```

Expected output: `Successfully installed pytest-...`

- [ ] **Step 2: Create requirements.txt**

```
pytest
matplotlib
numpy
pandas
```

- [ ] **Step 3: Create tests directory**

```bash
mkdir tests
touch tests/__init__.py
```

- [ ] **Step 4: Verify pytest runs**

```bash
venv/Scripts/pytest tests/ -v
```

Expected: `no tests ran` (0 collected) with exit code 0 (or 5 for "no tests").

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py
git commit -m "chore: add pytest and test directory"
```

---

## Task 2: SimulationState

**Files:**
- Rewrite: `state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_state.py`:

```python
from state import SimulationState, MacroState, Property, ActorState


def test_macro_state_defaults():
    m = MacroState()
    assert m.price_index == 100.0
    assert m.interest_rate == 0.05
    assert m.rent_growth == 0.03


def test_simulation_state_defaults():
    s = SimulationState()
    assert s.tick == 0
    assert s.current_scenario == "baseline"
    assert isinstance(s.macro, MacroState)
    assert s.properties == []
    assert s.actors == {}


def test_advance_tick():
    s = SimulationState()
    s.advance_tick()
    assert s.tick == 1


def test_property_fields():
    p = Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    assert p.id == "p1"
    assert p.base_value == 300000.0


def test_actor_state_defaults():
    a = ActorState(id="a1", name="Investor A", cash=100000.0, risk_appetite=0.6)
    assert a.portfolio == []
    assert a.cash == 100000.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_state.py -v
```

Expected: `ImportError` — `MacroState` not found.

- [ ] **Step 3: Rewrite state.py**

```python
from dataclasses import dataclass, field


@dataclass
class MacroState:
    price_index: float = 100.0
    interest_rate: float = 0.05
    rent_growth: float = 0.03


@dataclass
class Property:
    id: str
    region: str
    base_value: float
    current_value: float
    rent: float


@dataclass
class ActorState:
    id: str
    name: str
    cash: float
    risk_appetite: float
    portfolio: list = field(default_factory=list)


@dataclass
class SimulationState:
    tick: int = 0
    current_scenario: str = "baseline"
    macro: MacroState = field(default_factory=MacroState)
    properties: list = field(default_factory=list)
    actors: dict = field(default_factory=dict)

    def advance_tick(self):
        self.tick += 1
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_state.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: SimulationState with typed macro, property, and actor dataclasses"
```

---

## Task 3: ShockEngine

**Files:**
- Rewrite: `shocks.py`
- Create: `tests/test_shocks.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shocks.py`:

```python
from state import SimulationState
from shocks import ShockEngine, Shock


def test_delta_shock_mutates_interest_rate():
    state = SimulationState()
    engine = ShockEngine(shocks=[
        Shock(tick=1, shock_type="rate_hike", target="interest_rate", magnitude=0.02, mode="delta")
    ])
    engine.apply_shocks(state, tick=1)
    assert abs(state.macro.interest_rate - 0.07) < 1e-9


def test_multiplier_shock_mutates_price_index():
    state = SimulationState()
    engine = ShockEngine(shocks=[
        Shock(tick=1, shock_type="price_drop", target="price_index", magnitude=0.90, mode="multiplier")
    ])
    engine.apply_shocks(state, tick=1)
    assert abs(state.macro.price_index - 90.0) < 1e-9


def test_shock_only_fires_on_matching_tick():
    state = SimulationState()
    engine = ShockEngine(shocks=[
        Shock(tick=5, shock_type="rate_hike", target="interest_rate", magnitude=0.02, mode="delta")
    ])
    engine.apply_shocks(state, tick=1)
    assert state.macro.interest_rate == 0.05  # unchanged


def test_shock_returns_event_dict():
    state = SimulationState()
    engine = ShockEngine(shocks=[
        Shock(tick=1, shock_type="rate_hike", target="interest_rate", magnitude=0.02, mode="delta")
    ])
    events = engine.apply_shocks(state, tick=1)
    assert len(events) == 1
    assert events[0]["type"] == "shock"
    assert events[0]["tick"] == 1
    assert events[0]["shock_type"] == "rate_hike"


def test_no_shock_returns_empty_list():
    state = SimulationState()
    engine = ShockEngine(shocks=[])
    events = engine.apply_shocks(state, tick=1)
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_shocks.py -v
```

Expected: `ImportError` — `Shock` not found.

- [ ] **Step 3: Rewrite shocks.py**

```python
from dataclasses import dataclass


@dataclass
class Shock:
    tick: int
    shock_type: str
    target: str
    magnitude: float
    mode: str  # 'delta' or 'multiplier'


DEFAULT_SHOCKS = [
    Shock(tick=5, shock_type="rate_hike", target="interest_rate", magnitude=0.02, mode="delta"),
    Shock(tick=10, shock_type="price_drop", target="price_index", magnitude=0.90, mode="multiplier"),
]


class ShockEngine:
    def __init__(self, shocks=None):
        self.shocks = shocks if shocks is not None else DEFAULT_SHOCKS

    def apply_shocks(self, state, tick):
        events = []
        for shock in self.shocks:
            if shock.tick == tick:
                self._apply(state.macro, shock)
                events.append({
                    "type": "shock",
                    "tick": tick,
                    "shock_type": shock.shock_type,
                    "target": shock.target,
                    "magnitude": shock.magnitude,
                    "detail": f"{shock.shock_type}: {shock.target} {shock.mode} {shock.magnitude}",
                })
        return events

    def _apply(self, macro, shock):
        current = getattr(macro, shock.target)
        if shock.mode == "delta":
            setattr(macro, shock.target, current + shock.magnitude)
        else:
            setattr(macro, shock.target, current * shock.magnitude)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_shocks.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add shocks.py tests/test_shocks.py
git commit -m "feat: ShockEngine with delta and multiplier shock application"
```

---

## Task 4: ScenarioManager

**Files:**
- Rewrite: `scenarios.py`
- Create: `tests/test_scenarios.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scenarios.py`:

```python
from state import SimulationState
from scenarios import ScenarioManager, SCENARIO_CONFIGS


def test_baseline_drift_increases_price_index():
    state = SimulationState()
    manager = ScenarioManager(transitions=[])
    manager.advance(state, tick=1)
    assert state.macro.price_index > 100.0


def test_downturn_drift_decreases_price_index():
    state = SimulationState()
    state.current_scenario = "downturn"
    manager = ScenarioManager(transitions=[])
    manager.current_scenario = "downturn"
    manager.advance(state, tick=1)
    assert state.macro.price_index < 100.0


def test_scenario_transition_fires_on_correct_tick():
    state = SimulationState()
    manager = ScenarioManager(transitions=[(3, "downturn")])
    manager.advance(state, tick=3)
    assert state.current_scenario == "downturn"
    assert manager.current_scenario == "downturn"


def test_scenario_transition_does_not_fire_early():
    state = SimulationState()
    manager = ScenarioManager(transitions=[(3, "downturn")])
    manager.advance(state, tick=2)
    assert state.current_scenario == "baseline"


def test_advance_returns_event_dict():
    state = SimulationState()
    manager = ScenarioManager(transitions=[])
    events = manager.advance(state, tick=1)
    assert len(events) >= 1
    assert events[0]["type"] in ("scenario_advance", "scenario_transition")
    assert events[0]["tick"] == 1


def test_transition_event_type():
    state = SimulationState()
    manager = ScenarioManager(transitions=[(1, "downturn")])
    events = manager.advance(state, tick=1)
    transition_events = [e for e in events if e["type"] == "scenario_transition"]
    assert len(transition_events) == 1
    assert transition_events[0]["scenario"] == "downturn"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_scenarios.py -v
```

Expected: `ImportError` — `SCENARIO_CONFIGS` not found.

- [ ] **Step 3: Rewrite scenarios.py**

```python
SCENARIO_CONFIGS = {
    "baseline": {
        "price_index_drift": 0.5,
        "interest_rate_drift": 0.0,
        "rent_growth_drift": 0.0,
    },
    "downturn": {
        "price_index_drift": -1.0,
        "interest_rate_drift": 0.002,
        "rent_growth_drift": -0.005,
    },
    "recovery": {
        "price_index_drift": 0.75,
        "interest_rate_drift": -0.002,
        "rent_growth_drift": 0.003,
    },
}

DEFAULT_TRANSITIONS = [
    (8, "downturn"),
    (15, "recovery"),
]


class ScenarioManager:
    def __init__(self, transitions=None):
        self.current_scenario = "baseline"
        self.transitions = transitions if transitions is not None else DEFAULT_TRANSITIONS

    def advance(self, state, tick):
        events = []
        for t_tick, t_scenario in self.transitions:
            if t_tick == tick:
                self.current_scenario = t_scenario
                state.current_scenario = t_scenario
                events.append({
                    "type": "scenario_transition",
                    "tick": tick,
                    "scenario": t_scenario,
                    "detail": f"Scenario changed to {t_scenario}",
                })
        config = SCENARIO_CONFIGS[self.current_scenario]
        state.macro.price_index += config["price_index_drift"]
        state.macro.interest_rate += config["interest_rate_drift"]
        state.macro.rent_growth += config["rent_growth_drift"]
        if not events:
            events.append({
                "type": "scenario_advance",
                "tick": tick,
                "scenario": self.current_scenario,
                "detail": f"Scenario: {self.current_scenario}",
            })
        return events
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_scenarios.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scenarios.py tests/test_scenarios.py
git commit -m "feat: ScenarioManager with per-scenario macro drift and tick-based transitions"
```

---

## Task 5: PropertyModel

**Files:**
- Rewrite: `property_model.py`
- Create: `tests/test_property_model.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_property_model.py`:

```python
from state import SimulationState, Property
from property_model import PropertyModel


def test_value_update_uses_price_index():
    state = SimulationState()
    state.properties = [
        Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    ]
    state.macro.price_index = 110.0
    model = PropertyModel()
    model.update(state)
    assert abs(state.properties[0].current_value - 330000.0) < 0.01


def test_rent_update_compounds():
    state = SimulationState()
    state.properties = [
        Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    ]
    state.macro.rent_growth = 0.12  # 12% annual -> 1% monthly
    model = PropertyModel()
    model.update(state)
    assert abs(state.properties[0].rent - 1515.0) < 0.01


def test_update_returns_one_event_per_property():
    state = SimulationState()
    state.properties = [
        Property(id="p1", region="London", base_value=200000.0, current_value=200000.0, rent=1000.0),
        Property(id="p2", region="Manchester", base_value=150000.0, current_value=150000.0, rent=800.0),
    ]
    model = PropertyModel()
    events = model.update(state)
    assert len(events) == 2
    assert all(e["type"] == "property_valuation" for e in events)


def test_update_with_no_properties_returns_empty():
    state = SimulationState()
    model = PropertyModel()
    events = model.update(state)
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_property_model.py -v
```

Expected: `ImportError` or assertion errors.

- [ ] **Step 3: Rewrite property_model.py**

```python
class PropertyModel:
    def update(self, state):
        events = []
        for prop in state.properties:
            prop.current_value = prop.base_value * (state.macro.price_index / 100.0)
            prop.rent *= (1 + state.macro.rent_growth / 12)
            events.append({
                "type": "property_valuation",
                "tick": state.tick,
                "property_id": prop.id,
                "current_value": prop.current_value,
                "rent": prop.rent,
                "detail": f"Property {prop.id}: value={prop.current_value:.2f}, rent={prop.rent:.2f}",
            })
        return events
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_property_model.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add property_model.py tests/test_property_model.py
git commit -m "feat: PropertyModel computing current_value and rent per tick"
```

---

## Task 6: ActorManager

**Files:**
- Rewrite: `actors.py`
- Create: `tests/test_actors.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_actors.py`:

```python
from state import SimulationState, ActorState
from actors import ActorManager


def test_cash_compounds_at_interest_rate():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="Investor A", cash=100000.0, risk_appetite=0.5)
    }
    state.macro.interest_rate = 0.12  # 12% annual -> 1% monthly
    manager = ActorManager()
    manager.step(state, tick=1)
    assert abs(state.actors["a1"].cash - 101000.0) < 0.01


def test_step_returns_one_event_per_actor():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="A", cash=50000.0, risk_appetite=0.5),
        "a2": ActorState(id="a2", name="B", cash=75000.0, risk_appetite=0.7),
    }
    manager = ActorManager()
    events = manager.step(state, tick=1)
    assert len(events) == 2
    assert all(e["type"] == "actor_step" for e in events)


def test_step_with_no_actors_returns_empty():
    state = SimulationState()
    manager = ActorManager()
    events = manager.step(state, tick=1)
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_actors.py -v
```

Expected: assertion errors (placeholder returns wrong events).

- [ ] **Step 3: Rewrite actors.py**

```python
class ActorManager:
    def step(self, state, tick):
        events = []
        for actor_id, actor in state.actors.items():
            actor.cash *= (1 + state.macro.interest_rate / 12)
            events.append({
                "type": "actor_step",
                "tick": tick,
                "actor_id": actor_id,
                "cash": actor.cash,
                "detail": f"Actor {actor.name}: cash={actor.cash:.2f}",
            })
        return events
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_actors.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add actors.py tests/test_actors.py
git commit -m "feat: ActorManager applies monthly interest compounding to actor cash"
```

---

## Task 7: AIController

**Files:**
- Rewrite: `ai.py`
- Create: `tests/test_ai.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ai.py`:

```python
from state import SimulationState, ActorState
from ai import AIController


def _state_with_ai_actor(cash=100000.0, risk_appetite=0.6):
    state = SimulationState()
    state.actors = {
        "ai1": ActorState(id="ai1", name="AI Investor", cash=cash, risk_appetite=risk_appetite),
    }
    return state


def test_hold_when_interest_rate_is_high():
    state = _state_with_ai_actor()
    state.macro.interest_rate = 0.09  # above HIGH_RATE_THRESHOLD of 0.07
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_buy_when_price_low_and_cash_sufficient_and_risk_tolerant():
    state = _state_with_ai_actor(cash=100000.0, risk_appetite=0.8)
    state.macro.price_index = 90.0   # below LOW_PRICE_THRESHOLD of 95
    state.macro.interest_rate = 0.05  # below threshold
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "buy"


def test_no_buy_when_risk_appetite_low():
    state = _state_with_ai_actor(cash=100000.0, risk_appetite=0.3)
    state.macro.price_index = 90.0
    state.macro.interest_rate = 0.05
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_sell_when_price_high_and_has_portfolio():
    state = _state_with_ai_actor()
    state.actors["ai1"].portfolio = ["p1"]
    state.macro.price_index = 115.0  # above SELL_THRESHOLD of 110
    state.macro.interest_rate = 0.05
    controller = AIController()
    events = controller.step(state, tick=1)
    assert events[0]["action"] == "sell"


def test_step_returns_event_per_ai_actor():
    state = SimulationState()
    state.actors = {
        "ai1": ActorState(id="ai1", name="AI", cash=50000.0, risk_appetite=0.5),
        "ai2": ActorState(id="ai2", name="AI2", cash=60000.0, risk_appetite=0.4),
    }
    controller = AIController()
    events = controller.step(state, tick=1)
    assert len(events) == 2
    assert all(e["type"] == "ai_action" for e in events)


def test_player_actor_is_skipped():
    state = SimulationState()
    state.actors = {
        "player": ActorState(id="player", name="Player", cash=80000.0, risk_appetite=0.5),
        "ai1": ActorState(id="ai1", name="AI", cash=50000.0, risk_appetite=0.5),
    }
    controller = AIController()
    events = controller.step(state, tick=1)
    assert len(events) == 1
    assert events[0]["actor_id"] == "ai1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_ai.py -v
```

Expected: multiple assertion errors.

- [ ] **Step 3: Rewrite ai.py**

```python
HIGH_RATE_THRESHOLD = 0.07
LOW_PRICE_THRESHOLD = 95.0
SELL_PRICE_THRESHOLD = 110.0
MIN_CASH_TO_BUY = 50000.0


class AIController:
    def step(self, state, tick):
        events = []
        for actor_id, actor in state.actors.items():
            if actor_id == "player":
                continue
            action = self._decide(state, actor)
            events.append({
                "type": "ai_action",
                "tick": tick,
                "actor_id": actor_id,
                "action": action,
                "detail": f"AI {actor.name} decides: {action}",
            })
        return events

    def _decide(self, state, actor):
        macro = state.macro
        if macro.interest_rate > HIGH_RATE_THRESHOLD:
            return "hold"
        if (macro.price_index < LOW_PRICE_THRESHOLD
                and actor.cash >= MIN_CASH_TO_BUY
                and actor.risk_appetite > 0.5):
            return "buy"
        if macro.price_index > SELL_PRICE_THRESHOLD and len(actor.portfolio) > 0:
            return "sell"
        return "hold"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_ai.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add ai.py tests/test_ai.py
git commit -m "feat: AIController with interest rate, price, and risk-based decision tree"
```

---

## Task 8: Narrative Systems

**Files:**
- Rewrite: `narrative/branching.py`
- Rewrite: `narrative/scenario_events.py`
- Create: `tests/test_narrative.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_narrative.py`:

```python
from state import SimulationState
from narrative.branching import BranchingEngine, HIGH_RATE_THRESHOLD
from narrative.scenario_events import ScenarioEventEngine


def test_stress_branch_when_rate_high():
    state = SimulationState()
    state.macro.interest_rate = HIGH_RATE_THRESHOLD + 0.01
    engine = BranchingEngine()
    events = engine.step(state, tick=1)
    assert events[0]["branch"] == "stress"


def test_stable_branch_when_rate_normal():
    state = SimulationState()
    state.macro.interest_rate = 0.04
    engine = BranchingEngine()
    events = engine.step(state, tick=1)
    assert events[0]["branch"] == "stable"


def test_branching_returns_event_dict():
    state = SimulationState()
    engine = BranchingEngine()
    events = engine.step(state, tick=3)
    assert len(events) == 1
    assert events[0]["type"] == "narrative_branch"
    assert events[0]["tick"] == 3
    assert "detail" in events[0]


def test_scenario_event_returns_event_dict():
    state = SimulationState()
    state.current_scenario = "baseline"
    engine = ScenarioEventEngine()
    events = engine.step(state, tick=1)
    assert len(events) == 1
    assert events[0]["type"] == "scenario_event"
    assert isinstance(events[0]["detail"], str)
    assert len(events[0]["detail"]) > 0


def test_scenario_event_varies_by_scenario():
    engine = ScenarioEventEngine()
    baseline_state = SimulationState()
    baseline_state.current_scenario = "baseline"
    downturn_state = SimulationState()
    downturn_state.current_scenario = "downturn"
    baseline_events = engine.step(baseline_state, tick=1)
    downturn_events = engine.step(downturn_state, tick=1)
    # text should differ between scenarios
    assert baseline_events[0]["detail"] != downturn_events[0]["detail"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_narrative.py -v
```

Expected: `ImportError` — `HIGH_RATE_THRESHOLD` not found.

- [ ] **Step 3: Rewrite narrative/branching.py**

```python
HIGH_RATE_THRESHOLD = 0.07

_STRESS_TEXTS = [
    "High interest rates are squeezing landlord margins across the market.",
    "Mortgage costs rise sharply, putting pressure on leveraged investors.",
]

_STABLE_TEXTS = [
    "Market conditions remain within normal parameters.",
    "Investor sentiment holds steady as rates stay manageable.",
]


class BranchingEngine:
    def __init__(self):
        self._tick_counter = 0

    def step(self, state, tick):
        if state.macro.interest_rate > HIGH_RATE_THRESHOLD:
            branch = "stress"
            detail = _STRESS_TEXTS[self._tick_counter % len(_STRESS_TEXTS)]
        else:
            branch = "stable"
            detail = _STABLE_TEXTS[self._tick_counter % len(_STABLE_TEXTS)]
        self._tick_counter += 1
        return [{
            "type": "narrative_branch",
            "tick": tick,
            "branch": branch,
            "detail": detail,
        }]
```

- [ ] **Step 4: Rewrite narrative/scenario_events.py**

```python
_FLAVOUR = {
    "baseline": [
        "Property prices continue their steady upward trend.",
        "Mortgage approvals remain stable this quarter.",
        "New-build completions rise as developer confidence holds.",
    ],
    "downturn": [
        "Mortgage approvals fall to a 10-year low.",
        "Estate agents report a surge in forced sales.",
        "Buy-to-let landlords face mounting pressure as yields compress.",
    ],
    "recovery": [
        "First-time buyer activity picks up as rates begin to ease.",
        "Rental demand rises as market confidence slowly returns.",
        "House price falls slow as buyers return to the market.",
    ],
}


class ScenarioEventEngine:
    def __init__(self):
        self._tick_counter = 0

    def step(self, state, tick):
        texts = _FLAVOUR.get(state.current_scenario, _FLAVOUR["baseline"])
        detail = texts[self._tick_counter % len(texts)]
        self._tick_counter += 1
        return [{
            "type": "scenario_event",
            "tick": tick,
            "scenario": state.current_scenario,
            "detail": detail,
        }]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_narrative.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add narrative/branching.py narrative/scenario_events.py tests/test_narrative.py
git commit -m "feat: BranchingEngine and ScenarioEventEngine with scenario-aware narrative"
```

---

## Task 9: ScoringEngine

**Files:**
- Create: `scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scoring.py`:

```python
from state import SimulationState, ActorState, Property
from scoring import ScoringEngine


def _populated_state():
    state = SimulationState()
    state.properties = [
        Property(id="p1", region="London", base_value=300000.0, current_value=320000.0, rent=1600.0),
        Property(id="p2", region="Manchester", base_value=150000.0, current_value=160000.0, rent=900.0),
    ]
    state.actors = {
        "player": ActorState(id="player", name="Player", cash=50000.0, risk_appetite=0.5, portfolio=["p1"]),
        "ai1": ActorState(id="ai1", name="AI", cash=30000.0, risk_appetite=0.7, portfolio=["p2"]),
    }
    return state


def test_final_score_includes_portfolio_value_and_cash():
    state = _populated_state()
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    player_score = scores["player"]
    assert abs(player_score["portfolio_value"] - 320000.0) < 0.01
    assert abs(player_score["cash"] - 50000.0) < 0.01
    assert abs(player_score["final_score"] - 370000.0) < 0.01


def test_cumulative_rent_accumulates():
    state = _populated_state()
    engine = ScoringEngine()
    engine.record_rent("player", 1600.0)
    engine.record_rent("player", 1600.0)
    scores = engine.compute_scores(state)
    assert abs(scores["player"]["cumulative_rent"] - 3200.0) < 0.01
    assert abs(scores["player"]["final_score"] - 373200.0) < 0.01


def test_actor_with_no_properties_scores_only_cash():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="A", cash=20000.0, risk_appetite=0.5, portfolio=[])
    }
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    assert abs(scores["a1"]["final_score"] - 20000.0) < 0.01


def test_scores_include_all_actors():
    state = _populated_state()
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    assert "player" in scores
    assert "ai1" in scores
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_scoring.py -v
```

Expected: `ModuleNotFoundError` — `scoring` not found.

- [ ] **Step 3: Create scoring.py**

```python
class ScoringEngine:
    def __init__(self):
        self._cumulative_rent = {}

    def record_rent(self, actor_id, amount):
        self._cumulative_rent[actor_id] = self._cumulative_rent.get(actor_id, 0.0) + amount

    def compute_scores(self, state):
        property_map = {p.id: p for p in state.properties}
        scores = {}
        for actor_id, actor in state.actors.items():
            portfolio_value = sum(
                property_map[pid].current_value
                for pid in actor.portfolio
                if pid in property_map
            )
            cumulative_rent = self._cumulative_rent.get(actor_id, 0.0)
            scores[actor_id] = {
                "actor_id": actor_id,
                "name": actor.name,
                "portfolio_value": portfolio_value,
                "cash": actor.cash,
                "cumulative_rent": cumulative_rent,
                "final_score": portfolio_value + actor.cash + cumulative_rent,
            }
        return scores

    def leaderboard(self, state):
        scores = self.compute_scores(state)
        return sorted(scores.values(), key=lambda s: s["final_score"], reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_scoring.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scoring.py tests/test_scoring.py
git commit -m "feat: ScoringEngine with per-actor portfolio value, cash, and cumulative rent"
```

---

## Task 10: Kernel Wiring

**Files:**
- Rewrite: `kernel.py`
- Create: `tests/test_kernel.py`

The kernel needs: `advance_tick` called each turn, `PropertyModel` wired in, `ScoringEngine` wired in, configurable turn count, and seed data so the simulation has actors and properties.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_kernel.py`:

```python
from kernel import SimulationKernel


def test_run_returns_trace_with_correct_tick_count():
    kernel = SimulationKernel(turns=5)
    results = kernel.run()
    assert len(results["trace"]) == 5


def test_state_tick_advances_each_turn():
    kernel = SimulationKernel(turns=3)
    kernel.run()
    assert kernel.state.tick == 3


def test_trace_contains_property_valuation_events():
    kernel = SimulationKernel(turns=2)
    results = kernel.run()
    all_events = [e for tick in results["trace"] for e in tick["events"]]
    valuation_events = [e for e in all_events if e["type"] == "property_valuation"]
    assert len(valuation_events) > 0


def test_trace_contains_shock_events_on_correct_tick():
    from shocks import Shock
    kernel = SimulationKernel(turns=3, shocks=[
        Shock(tick=2, shock_type="rate_hike", target="interest_rate", magnitude=0.01, mode="delta")
    ])
    results = kernel.run()
    tick_2_events = results["trace"][1]["events"]  # tick index 1 = tick value 2
    shock_events = [e for e in tick_2_events if e["type"] == "shock"]
    assert len(shock_events) == 1


def test_leaderboard_present_in_results():
    kernel = SimulationKernel(turns=2)
    results = kernel.run()
    assert "leaderboard" in results
    assert len(results["leaderboard"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_kernel.py -v
```

Expected: errors — `SimulationKernel` doesn't accept `turns` or `shocks` args.

- [ ] **Step 3: Rewrite kernel.py**

```python
from state import SimulationState, Property, ActorState
from scenarios import ScenarioManager
from shocks import ShockEngine
from actors import ActorManager
from ai import AIController
from narrative.branching import BranchingEngine
from narrative.scenario_events import ScenarioEventEngine
from player.choices import PlayerChoiceEngine
from property_model import PropertyModel
from scoring import ScoringEngine
from ui.event_log_state import EventLogState
from ui.event_log_components import EventLogComponents


def _default_properties():
    return [
        Property(id="p1", region="London", base_value=400000.0, current_value=400000.0, rent=2000.0),
        Property(id="p2", region="Manchester", base_value=200000.0, current_value=200000.0, rent=1100.0),
        Property(id="p3", region="Birmingham", base_value=180000.0, current_value=180000.0, rent=950.0),
    ]


def _default_actors():
    return {
        "player": ActorState(id="player", name="Player", cash=150000.0, risk_appetite=0.6, portfolio=["p1"]),
        "ai1": ActorState(id="ai1", name="Conservative AI", cash=120000.0, risk_appetite=0.3, portfolio=["p2"]),
        "ai2": ActorState(id="ai2", name="Aggressive AI", cash=100000.0, risk_appetite=0.9, portfolio=["p3"]),
    }


class SimulationKernel:
    def __init__(self, turns=20, shocks=None, transitions=None):
        self.turns = turns
        self.state = SimulationState()
        self.state.properties = _default_properties()
        self.state.actors = _default_actors()
        self.scenarios = ScenarioManager(transitions=transitions)
        self.shocks = ShockEngine(shocks=shocks)
        self.actors = ActorManager()
        self.ai = AIController()
        self.branching = BranchingEngine()
        self.scenario_events = ScenarioEventEngine()
        self.player_choices = PlayerChoiceEngine()
        self.property_model = PropertyModel()
        self.scoring = ScoringEngine()
        self.event_log = EventLogState()
        self.renderer = EventLogComponents()

    def run(self):
        trace = []
        for _ in range(self.turns):
            self.state.advance_tick()
            tick = self.state.tick
            tick_events = []
            tick_events += self.shocks.apply_shocks(self.state, tick)
            tick_events += self.scenarios.advance(self.state, tick)
            tick_events += self.actors.step(self.state, tick)
            tick_events += self.ai.step(self.state, tick)
            tick_events += self.player_choices.step(self.state, tick)
            tick_events += self.branching.step(self.state, tick)
            tick_events += self.scenario_events.step(self.state, tick)
            tick_events += self.property_model.update(self.state)
            self.event_log.append_events(tick_events)
            trace.append({"tick": tick, "events": tick_events})
        leaderboard = self.scoring.leaderboard(self.state)
        return {"trace": trace, "leaderboard": leaderboard}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_kernel.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
venv/Scripts/pytest tests/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add kernel.py tests/test_kernel.py
git commit -m "feat: SimulationKernel fully wired with all phases, property model, and scoring"
```

---

## Task 11: Visualisation

**Files:**
- Create: `visualisation/__init__.py`
- Create: `visualisation/shock_timeline.py`
- Create: `visualisation/scenario_transitions.py`
- Delete: `scenario_transitions.py` (root — now misplaced visualisation code)

- [ ] **Step 1: Create visualisation directory and __init__.py**

```bash
mkdir visualisation
touch visualisation/__init__.py
```

- [ ] **Step 2: Create visualisation/shock_timeline.py**

```python
import matplotlib.pyplot as plt


def plot_shock_timeline(trace):
    ticks = []
    labels = []
    for entry in trace:
        for event in entry["events"]:
            if event["type"] == "shock":
                ticks.append(entry["tick"])
                labels.append(event.get("shock_type", "shock"))

    fig, ax = plt.subplots(figsize=(10, 3))
    for i, (tick, label) in enumerate(zip(ticks, labels)):
        ax.axvline(x=tick, color="red", linestyle="--", alpha=0.7)
        ax.text(tick, 0.5 + (i % 2) * 0.3, label, rotation=45, fontsize=8, color="red")

    all_ticks = [e["tick"] for e in trace]
    ax.set_xlim(min(all_ticks) - 0.5, max(all_ticks) + 0.5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Tick")
    ax.set_title("Shock Timeline")
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig("shock_timeline.png")
    plt.close()
    print("Saved shock_timeline.png")
```

- [ ] **Step 3: Create visualisation/scenario_transitions.py**

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

SCENARIO_COLOURS = {
    "baseline": "#209dd7",
    "downturn": "#c0392b",
    "recovery": "#27ae60",
}


def plot_scenario_transitions(trace):
    ticks = [e["tick"] for e in trace]
    scenario_by_tick = {}
    for entry in trace:
        for event in entry["events"]:
            if event["type"] in ("scenario_advance", "scenario_transition"):
                scenario_by_tick[entry["tick"]] = event.get("scenario", "baseline")

    fig, ax = plt.subplots(figsize=(10, 2))
    for tick in ticks:
        scenario = scenario_by_tick.get(tick, "baseline")
        colour = SCENARIO_COLOURS.get(scenario, "#888888")
        ax.barh(0, 1, left=tick - 1, height=0.8, color=colour, align="edge")

    patches = [mpatches.Patch(color=c, label=s) for s, c in SCENARIO_COLOURS.items()]
    ax.legend(handles=patches, loc="upper right")
    ax.set_xlabel("Tick")
    ax.set_title("Scenario Transitions")
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig("scenario_transitions.png")
    plt.close()
    print("Saved scenario_transitions.png")
```

- [ ] **Step 4: Delete the misplaced root scenario_transitions.py**

```bash
rm scenario_transitions.py
```

- [ ] **Step 5: Run main.py to verify end-to-end**

```bash
venv/Scripts/python main.py
```

Expected output:
```
Saved shock_timeline.png
Saved scenario_transitions.png
Simulation complete.
```

And two PNG files in the project root.

- [ ] **Step 6: Commit**

```bash
git add visualisation/ main.py
git rm scenario_transitions.py
git commit -m "feat: matplotlib visualisation for shock timeline and scenario transitions"
```

---

## Task 12: End-to-End Smoke Test and Leaderboard Output

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py to print the leaderboard**

```python
from kernel import SimulationKernel
from visualisation.shock_timeline import plot_shock_timeline
from visualisation.scenario_transitions import plot_scenario_transitions


def main():
    kernel = SimulationKernel(turns=20)
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

    print("\nSimulation complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full simulation**

```bash
venv/Scripts/python main.py
```

Expected output (values will vary):
```
Saved shock_timeline.png
Saved scenario_transitions.png

=== LEADERBOARD ===
  1. Player               Score: £   580,000  (Portfolio: £   420,000  Cash: £  160,000)
  2. Aggressive AI        Score: £   315,000  (Portfolio: £   210,000  Cash: £  105,000)
  3. Conservative AI      Score: £   290,000  (Portfolio: £   200,000  Cash: £   90,000)

Simulation complete.
```

- [ ] **Step 3: Run the full test suite one final time**

```bash
venv/Scripts/pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: leaderboard output in main.py — simulation fully runnable end-to-end"
```

---

## Self-Review Against game.md

| Spec Section | Covered | Notes |
|---|---|---|
| §2 Time structure (20/40 turns) | Yes | `turns` param on kernel; default 20 |
| §3 Core loop phase order | Yes | kernel.py matches spec order |
| §3.1 Macro state fields | Yes | MacroState dataclass |
| §3.2 Property state | Yes | Property dataclass |
| §3.3 Actor state | Yes | ActorState dataclass |
| §4 Shock system (delta/multiplier) | Yes | ShockEngine |
| §5 Scenario system with drift | Yes | ScenarioManager + SCENARIO_CONFIGS |
| §6.1 Value formula | Yes | PropertyModel |
| §6.2 Rent formula | Yes | PropertyModel |
| §7.1 Cash compounding | Yes | ActorManager |
| §7.2 Actor actions | Partial | AI decides; player is stub (interactive input is future) |
| §8 AI decision tree | Yes | AIController |
| §9.1 Branching engine | Yes | BranchingEngine |
| §9.2 Scenario event engine | Yes | ScenarioEventEngine |
| §10 Event log | Yes | EventLogState |
| §11 Scoring formula | Yes | ScoringEngine |
| §11.3 Leaderboard | Yes | leaderboard() method |
| §12 AI benchmarking (decision trace) | Partial | trace in results; per-turn scoring not separate |
| §13 Visualisation | Yes | shock_timeline.py, scenario_transitions.py |
| §14 Future extensions | — | Not in scope |
