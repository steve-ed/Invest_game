# Game Investment Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the simulation from a passive wealth-tracking exercise into an active investment game where all actors (player and AIs) make meaningful buy/sell/upgrade decisions driven by acquisition strategies, with mortgages, transaction costs, EPC compliance, and risk-adjusted scoring.

**Architecture:** Seven sequential tasks build on each other — property archetypes and EPC data first, then the financial mechanics (mortgage, SDLT), then strategy-aware AI, then EPC shocks, then the player browser action panel, and finally richer scoring. Each task is independently testable and committable.

**Tech Stack:** Python 3.11, dataclasses, Flask (existing), Chart.js 4.x (existing), pytest. No new dependencies.

---

## File Structure

**Modified:**
- `state.py` — add archetype, epc_band, age, mortgage fields to `Property`; add strategy, rent/cost accumulators to `ActorState`
- `kernel.py` — update `_default_properties()`, `_default_actors()`, `_execute_action()`, add SDLT/EPC helpers, read player action, set `initial_wealth`, reorder property_model before actors in tick loop
- `actors.py` — add rent collection, mortgage payment, fix interest period to semi-annual
- `property_model.py` — fix rent growth period to semi-annual (`/2`), handle void ticks, apply EPC upgrade effects
- `ai.py` — replace single `_decide()` with strategy-specific methods per actor
- `shocks.py` — add `epc_mandate` event type
- `scoring.py` — add risk score, risk-adjusted return, income/capital split to leaderboard
- `visualisation/dashboard_server.py` — add `POST /action` endpoint
- `player/choices.py` — read action from `player_action.json` instead of hardcoded hold
- `static/dashboard.html` — add player action panel to sidebar, EPC warning badges, scoring breakdown

**Created:**
- `tests/test_mortgage.py`
- `tests/test_transaction_costs.py`
- `tests/test_ai_strategies.py`
- `tests/test_epc.py`
- `tests/test_player_action.py`
- `tests/test_scoring_extended.py`

---

## Task 1: Property Archetypes and EPC Bands

Add `archetype`, `epc_band`, `age`, `void_ticks_remaining`, `mortgage_balance`, `mortgage_rate`, `is_fixed_rate` to `Property`. Add `strategy`, `total_rent_received`, `total_mortgage_paid`, `total_transaction_costs`, `initial_wealth` to `ActorState`. Update `_default_properties()` and `_default_actors()`.

**Files:**
- Modify: `state.py`
- Modify: `kernel.py` — `_default_properties()` lines 25–46, `_default_actors()` lines 49–57
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write failing tests for new Property fields**

```python
# tests/test_state.py — append these tests

def test_property_has_archetype():
    p = Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    assert p.archetype == "btl"

def test_property_has_epc_band():
    p = Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    assert p.epc_band == 4

def test_property_has_age():
    p = Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    assert p.age == 40

def test_property_has_mortgage_fields():
    p = Property(id="p1", region="London", base_value=300000.0, current_value=300000.0, rent=1500.0)
    assert p.mortgage_balance == 0.0
    assert p.mortgage_rate == 0.0
    assert p.is_fixed_rate == False
    assert p.void_ticks_remaining == 0

def test_actor_has_strategy():
    a = ActorState(id="a1", name="Inv", cash=100000.0, risk_appetite=0.5)
    assert a.strategy == "balanced"

def test_actor_has_accumulators():
    a = ActorState(id="a1", name="Inv", cash=100000.0, risk_appetite=0.5)
    assert a.total_rent_received == 0.0
    assert a.total_mortgage_paid == 0.0
    assert a.total_transaction_costs == 0.0
    assert a.initial_wealth == 0.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_state.py::test_property_has_archetype -v
```
Expected: FAIL with `TypeError` (unexpected keyword argument or missing field)

- [ ] **Step 3: Update `state.py`**

```python
from dataclasses import dataclass, field


@dataclass
class MacroState:
    price_index: float = 100.0
    interest_rate: float = 0.05
    rent_growth: float = 0.03


@dataclass
class MacroSnapshot:
    tick: int
    scenario: str
    price_index: float
    interest_rate: float
    rent_growth: float
    events: list


@dataclass
class Property:
    id: str
    region: str
    base_value: float
    current_value: float
    rent: float                        # monthly rent (£)
    archetype: str = "btl"            # btl | hmo | short_let | new_build | value_add
    epc_band: int = 4                 # 1=A (best) … 7=G (worst)
    age: int = 40                     # years
    mortgage_balance: float = 0.0
    mortgage_rate: float = 0.0        # fixed at purchase if is_fixed_rate
    is_fixed_rate: bool = False
    void_ticks_remaining: int = 0     # ticks of zero rent after acquisition


@dataclass
class ActorState:
    id: str
    name: str
    cash: float
    risk_appetite: float
    portfolio: list = field(default_factory=list)
    strategy: str = "balanced"        # yield | capital | value_add | brrr | leverage | demographic | balanced
    total_rent_received: float = 0.0
    total_mortgage_paid: float = 0.0
    total_transaction_costs: float = 0.0
    initial_wealth: float = 0.0


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

- [ ] **Step 4: Update `_default_properties()` in `kernel.py`**

Replace the existing `_default_properties` function (lines 25–46) with:

```python
def _default_properties():
    return [
        Property(id="p01", region="London Kensington",   base_value=500000.0, current_value=500000.0, rent=2500.0, archetype="btl",       epc_band=3, age=60),
        Property(id="p02", region="Oxford",              base_value=230000.0, current_value=230000.0, rent=1150.0, archetype="btl",       epc_band=4, age=50),
        Property(id="p03", region="Brighton",            base_value=220000.0, current_value=220000.0, rent=1100.0, archetype="btl",       epc_band=4, age=45),
        Property(id="p04", region="Sheffield",           base_value=130000.0, current_value=130000.0, rent=650.0,  archetype="value_add", epc_band=5, age=80),
        Property(id="p05", region="Leicester",           base_value=140000.0, current_value=140000.0, rent=700.0,  archetype="value_add", epc_band=5, age=75),
        Property(id="p06", region="Bristol",             base_value=260000.0, current_value=260000.0, rent=1300.0, archetype="btl",       epc_band=3, age=35),
        Property(id="p07", region="Cambridge",           base_value=250000.0, current_value=250000.0, rent=1250.0, archetype="btl",       epc_band=3, age=30),
        Property(id="p08", region="Birmingham",          base_value=200000.0, current_value=200000.0, rent=1000.0, archetype="value_add", epc_band=5, age=70),
        Property(id="p09", region="Manchester",          base_value=240000.0, current_value=240000.0, rent=1200.0, archetype="btl",       epc_band=4, age=40),
        Property(id="p10", region="Leeds",               base_value=170000.0, current_value=170000.0, rent=850.0,  archetype="value_add", epc_band=5, age=65),
        Property(id="p11", region="Nottingham",          base_value=155000.0, current_value=155000.0, rent=775.0,  archetype="hmo",       epc_band=5, age=70),
        Property(id="p12", region="Liverpool",           base_value=145000.0, current_value=145000.0, rent=725.0,  archetype="hmo",       epc_band=6, age=85),
        Property(id="p13", region="Cardiff",             base_value=160000.0, current_value=160000.0, rent=800.0,  archetype="btl",       epc_band=4, age=55),
        Property(id="p14", region="Newcastle",           base_value=120000.0, current_value=120000.0, rent=600.0,  archetype="value_add", epc_band=6, age=90),
        Property(id="p15", region="Sunderland",          base_value=90000.0,  current_value=90000.0,  rent=540.0,  archetype="value_add", epc_band=7, age=95),
        Property(id="m1",  region="London Shoreditch",   base_value=420000.0, current_value=420000.0, rent=1470.0, archetype="short_let", epc_band=2, age=15),
        Property(id="m2",  region="Bristol Harbourside", base_value=230000.0, current_value=230000.0, rent=1035.0, archetype="new_build", epc_band=1, age=2),
        Property(id="m3",  region="Leeds City Centre",   base_value=155000.0, current_value=155000.0, rent=930.0,  archetype="hmo",       epc_band=4, age=30),
        Property(id="m4",  region="Sunderland Dockside", base_value=80000.0,  current_value=80000.0,  rent=560.0,  archetype="value_add", epc_band=6, age=100),
    ]
```

- [ ] **Step 5: Update `_default_actors()` in `kernel.py`**

Replace lines 49–57:

```python
def _default_actors():
    return {
        "player": ActorState(id="player", name="Player",           cash=280000.0, risk_appetite=0.6, strategy="balanced",
                             portfolio=["p01", "p02", "p03", "p04", "p05"]),
        "ai1":   ActorState(id="ai1",   name="Conservative AI",   cash=790000.0, risk_appetite=0.3, strategy="yield",
                             portfolio=["p06", "p07", "p08"]),
        "ai2":   ActorState(id="ai2",   name="Aggressive AI",     cash=420000.0, risk_appetite=0.9, strategy="leverage",
                             portfolio=["p09", "p10", "p11", "p12", "p13", "p14", "p15"]),
    }
```

- [ ] **Step 6: Set `initial_wealth` at game start in `kernel.py` `__init__`**

After `self.scoring = ScoringEngine()` add:

```python
        for actor in self.state.actors.values():
            pv = _portfolio_value(actor, self.state.properties)
            actor.initial_wealth = actor.cash + pv
```

- [ ] **Step 7: Run all tests to confirm passing**

```
pytest tests/test_state.py -v
```
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add state.py kernel.py tests/test_state.py
git commit -m "feat: property archetypes, EPC bands, actor strategies"
```

---

## Task 2: Rent Collection, Mortgage Payments, and Period Fixes

Fix `property_model.py` rent growth to semi-annual. Add rent collection and mortgage payment to `actors.py`. Reorder `property_model.update` before `actors.step` in the kernel tick loop so actors collect the freshly updated rent.

**Files:**
- Modify: `property_model.py`
- Modify: `actors.py`
- Modify: `kernel.py` — tick loop order
- Create: `tests/test_mortgage.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mortgage.py
from state import Property, ActorState, SimulationState, MacroState
from actors import ActorManager


def _make_state(interest_rate=0.05, rent_growth=0.03):
    prop = Property(id="p1", region="London", base_value=300000.0,
                    current_value=300000.0, rent=1500.0)
    actor = ActorState(id="a1", name="Inv", cash=50000.0, risk_appetite=0.5,
                       portfolio=["p1"])
    state = SimulationState()
    state.macro = MacroState(price_index=100.0, interest_rate=interest_rate,
                             rent_growth=rent_growth)
    state.properties = [prop]
    state.actors = {"a1": actor}
    return state, prop, actor


def test_rent_collected_each_tick():
    state, prop, actor = _make_state()
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    # monthly rent=1500, semi-annual = 1500*6 = 9000
    assert actor.cash == pytest.approx(initial_cash + 9000, rel=1e-3)


def test_rent_accumulates_on_actor():
    state, prop, actor = _make_state()
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert actor.total_rent_received == pytest.approx(9000, rel=1e-3)


def test_void_period_suppresses_rent():
    state, prop, actor = _make_state()
    prop.void_ticks_remaining = 1
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    assert actor.cash == pytest.approx(initial_cash, rel=1e-3)
    assert prop.void_ticks_remaining == 0


def test_void_decrements_each_tick():
    state, prop, actor = _make_state()
    prop.void_ticks_remaining = 2
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert prop.void_ticks_remaining == 1


def test_mortgage_interest_deducted_semi_annually():
    state, prop, actor = _make_state(interest_rate=0.06)
    prop.mortgage_balance = 200000.0
    prop.mortgage_rate = 0.06
    prop.is_fixed_rate = True
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    # interest = 200000 * 0.06 / 2 = 6000
    # rent income = 1500 * 6 = 9000
    # savings interest on cash ≈ small
    expected = initial_cash + 9000 - 6000
    assert actor.cash == pytest.approx(expected, rel=1e-2)


def test_mortgage_uses_variable_rate_when_not_fixed():
    state, prop, actor = _make_state(interest_rate=0.08)
    prop.mortgage_balance = 100000.0
    prop.mortgage_rate = 0.05   # fixed rate — ignored when is_fixed_rate=False
    prop.is_fixed_rate = False
    mgr = ActorManager()
    initial_cash = actor.cash
    mgr.step(state, tick=1)
    # uses current rate 0.08: 100000 * 0.08 / 2 = 4000
    rent = 1500 * 6  # 9000
    expected = initial_cash + rent - 4000
    assert actor.cash == pytest.approx(expected, rel=1e-2)


def test_mortgage_paid_accumulates():
    state, prop, actor = _make_state(interest_rate=0.06)
    prop.mortgage_balance = 200000.0
    prop.mortgage_rate = 0.06
    prop.is_fixed_rate = True
    mgr = ActorManager()
    mgr.step(state, tick=1)
    assert actor.total_mortgage_paid == pytest.approx(6000, rel=1e-2)


import pytest
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_mortgage.py -v
```
Expected: FAIL — `ActorManager.step` only does cash interest, no rent or mortgage

- [ ] **Step 3: Rewrite `actors.py`**

```python
class ActorManager:
    def step(self, state, tick):
        prop_map = {p.id: p for p in state.properties}
        events = []

        for actor_id, actor in state.actors.items():
            # Savings interest on cash: BoE rate * 0.3, semi-annual
            savings_rate = state.macro.interest_rate * 0.3 / 2
            actor.cash *= (1 + savings_rate)

            # Mortgage payments (semi-annual interest)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop and prop.mortgage_balance > 0:
                    rate = prop.mortgage_rate if prop.is_fixed_rate else state.macro.interest_rate
                    interest = prop.mortgage_balance * rate / 2
                    actor.cash -= interest
                    actor.total_mortgage_paid += interest

            # Rent collection (monthly rent × 6 months per semi-annual tick)
            for pid in actor.portfolio:
                prop = prop_map.get(pid)
                if prop is None:
                    continue
                if prop.void_ticks_remaining > 0:
                    prop.void_ticks_remaining -= 1
                else:
                    income = prop.rent * 6
                    actor.cash += income
                    actor.total_rent_received += income

            events.append({
                "type": "actor_step",
                "tick": tick,
                "actor_id": actor_id,
                "cash": actor.cash,
                "detail": f"Actor {actor.name}: cash={actor.cash:.2f}",
            })

        return events
```

- [ ] **Step 4: Fix `property_model.py` rent growth period**

```python
class PropertyModel:
    def update(self, state):
        events = []
        for prop in state.properties:
            prop.current_value = prop.base_value * (state.macro.price_index / 100.0)
            # semi-annual rent growth (rent_growth is annual decimal)
            prop.rent *= (1 + state.macro.rent_growth / 2)
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

- [ ] **Step 5: Reorder tick loop in `kernel.py` `run()`**

In the tick loop, move `property_model.update` before `actors.step` so actors collect freshly updated rent. Replace lines 224–248 with:

```python
            tick_events += self.property_model.update(self.state)

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
```

- [ ] **Step 6: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS (smoke tests may need `turn_delay=0` — already set)

- [ ] **Step 7: Commit**

```bash
git add actors.py property_model.py kernel.py tests/test_mortgage.py
git commit -m "feat: rent collection, mortgage payments, semi-annual period fix"
```

---

## Task 3: Transaction Costs — SDLT, Agent Fees, Void Period, EPC Capex

Update `_execute_action` in `kernel.py` to deduct SDLT on buy, agent fee on sell, set void period on acquisition, and support EPC upgrade action. Add `_calculate_sdlt` and `_epc_upgrade_cost` helpers.

**Files:**
- Modify: `kernel.py` — `_execute_action()`, add two helpers
- Create: `tests/test_transaction_costs.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_transaction_costs.py
import pytest
from kernel import SimulationKernel, _calculate_sdlt, _epc_upgrade_cost
from state import Property, ActorState, SimulationState, MacroState


def test_sdlt_zero_below_125k():
    assert _calculate_sdlt(100_000) == pytest.approx(3_000)   # 3% surcharge only


def test_sdlt_at_250k():
    # 125k @ 3% = 3750, 125k @ 5% = 6250 → total 10000
    assert _calculate_sdlt(250_000) == pytest.approx(10_000)


def test_sdlt_at_500k():
    # 125k@3%=3750, 125k@5%=6250, 250k@8%=20000 → 30000
    assert _calculate_sdlt(500_000) == pytest.approx(30_000)


def test_epc_upgrade_cost_band_4():
    assert _epc_upgrade_cost(4) == 5_000   # D→C


def test_epc_upgrade_cost_band_5():
    assert _epc_upgrade_cost(5) == 12_000  # E→C


def test_epc_upgrade_cost_band_6():
    assert _epc_upgrade_cost(6) == 20_000  # F→C


def test_epc_upgrade_cost_band_7():
    assert _epc_upgrade_cost(7) == 30_000  # G→C


def _make_buy_state(price=200_000, cash=300_000, ltv=0.0):
    prop = Property(id="px", region="Test", base_value=price,
                    current_value=price, rent=800.0, epc_band=4)
    actor = ActorState(id="a1", name="Inv", cash=cash, risk_appetite=0.5)
    state = SimulationState()
    state.macro = MacroState(price_index=100.0, interest_rate=0.05, rent_growth=0.03)
    state.properties = [prop]
    state.actors = {"a1": actor}
    return state, prop, actor


def test_buy_deducts_sdlt():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    from kernel import SimulationKernel
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.0})
    sdlt = _calculate_sdlt(200_000)
    expected_cash = 300_000 - 200_000 - sdlt
    assert actor.cash == pytest.approx(expected_cash, rel=1e-3)


def test_buy_sets_void_period():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    from kernel import SimulationKernel
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.0})
    assert prop.void_ticks_remaining == 1


def test_buy_with_mortgage_sets_balance():
    state, prop, actor = _make_buy_state(price=200_000, cash=300_000)
    from kernel import SimulationKernel
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "buy", "property_id": "px",
                        "ltv": 0.75})
    assert prop.mortgage_balance == pytest.approx(150_000)
    deposit = 200_000 * 0.25
    sdlt = _calculate_sdlt(200_000)
    assert actor.cash == pytest.approx(300_000 - deposit - sdlt, rel=1e-3)


def test_sell_deducts_agent_fee_and_repays_mortgage():
    state, prop, actor = _make_buy_state(price=200_000, cash=10_000)
    prop.mortgage_balance = 120_000
    actor.portfolio = ["px"]
    from kernel import SimulationKernel
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "sell", "property_id": "px"})
    agent_fee = 200_000 * 0.015
    net = 200_000 - 120_000 - agent_fee
    assert actor.cash == pytest.approx(10_000 + net, rel=1e-3)
    assert "px" not in actor.portfolio


def test_upgrade_reduces_epc_band_and_deducts_cost():
    state, prop, actor = _make_buy_state(price=200_000, cash=50_000)
    prop.epc_band = 5
    actor.portfolio = ["px"]
    from kernel import SimulationKernel
    k = SimulationKernel(turns=1, turn_delay=0)
    k.state = state
    k._execute_action({"actor_id": "a1", "action": "upgrade", "property_id": "px"})
    assert prop.epc_band == 3        # E→C (two bands improvement)
    cost = _epc_upgrade_cost(5)
    assert actor.cash == pytest.approx(50_000 - cost, rel=1e-3)
    assert actor.total_transaction_costs == pytest.approx(cost, rel=1e-3)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_transaction_costs.py -v
```
Expected: FAIL — `_calculate_sdlt` and `_epc_upgrade_cost` not defined

- [ ] **Step 3: Add helpers and rewrite `_execute_action` in `kernel.py`**

Add after the `_portfolio_value` function (line 60):

```python
def _calculate_sdlt(price: float) -> float:
    """SDLT for additional residential property (3% surcharge applies to all bands)."""
    bands = [
        (125_000, 0.03),
        (125_000, 0.05),
        (675_000, 0.08),
        (575_000, 0.13),
    ]
    tax, remaining = 0.0, price
    for band_size, rate in bands:
        taxable = min(remaining, band_size)
        tax += taxable * rate
        remaining -= taxable
        if remaining <= 0:
            break
    if remaining > 0:
        tax += remaining * 0.15
    return round(tax, 2)


def _epc_upgrade_cost(epc_band: int) -> float:
    """Estimated retrofit cost to bring property to EPC C."""
    return {4: 5_000, 5: 12_000, 6: 20_000, 7: 30_000}.get(epc_band, 0.0)
```

Replace `_execute_action` in `kernel.py`:

```python
    def _execute_action(self, event):
        actor_id  = event.get("actor_id")
        action    = event.get("action")
        property_id = event.get("property_id")
        ltv       = event.get("ltv", 0.0)

        if not actor_id or action in ("hold", None) or not property_id:
            return

        actor = self.state.actors.get(actor_id)
        if not actor:
            return

        prop_map  = {p.id: p for p in self.state.properties}
        owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}
        prop = prop_map.get(property_id)
        if not prop:
            return

        if action == "sell" and property_id in actor.portfolio:
            agent_fee = prop.current_value * 0.015
            net = prop.current_value - prop.mortgage_balance - agent_fee
            actor.cash += net
            actor.total_transaction_costs += agent_fee
            prop.mortgage_balance = 0.0
            prop.mortgage_rate = 0.0
            prop.is_fixed_rate = False
            actor.portfolio.remove(property_id)

        elif action == "buy" and property_id not in owned_all:
            deposit  = prop.current_value * (1 - ltv)
            sdlt     = _calculate_sdlt(prop.current_value)
            total_outlay = deposit + sdlt
            if actor.cash >= total_outlay:
                actor.cash -= total_outlay
                actor.total_transaction_costs += sdlt
                prop.mortgage_balance = prop.current_value * ltv
                prop.mortgage_rate = self.state.macro.interest_rate
                prop.is_fixed_rate = False
                prop.void_ticks_remaining = 1
                actor.portfolio.append(property_id)

        elif action == "upgrade" and property_id in actor.portfolio:
            cost = _epc_upgrade_cost(prop.epc_band)
            if cost > 0 and actor.cash >= cost:
                actor.cash -= cost
                actor.total_transaction_costs += cost
                prop.epc_band = max(1, prop.epc_band - 2)  # improve two bands, minimum A
                prop.rent *= 1.10                           # 10% rent uplift post-upgrade
```

- [ ] **Step 4: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add kernel.py tests/test_transaction_costs.py
git commit -m "feat: SDLT, agent fees, void period, EPC upgrade action"
```

---

## Task 4: Strategy-Aware AI Decisions

Replace the single `_decide()` in `ai.py` with strategy-specific methods. Conservative AI uses `"yield"` strategy (buys when gross yield > 6%, rate < 7%). Aggressive AI uses `"leverage"` strategy (buys aggressively at low rates with 75% LTV, sells on rate spikes).

**Files:**
- Modify: `ai.py`
- Create: `tests/test_ai_strategies.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ai_strategies.py
import pytest
from ai import AIController
from state import Property, ActorState, SimulationState, MacroState


def _make_state(rate=0.05, price_index=100.0, rent_growth=0.03):
    state = SimulationState()
    state.macro = MacroState(price_index=price_index, interest_rate=rate,
                              rent_growth=rent_growth)
    return state


def _prop(pid, value, rent, epc_band=4):
    return Property(id=pid, region="Test", base_value=value,
                    current_value=value, rent=rent, epc_band=epc_band)


def test_yield_ai_buys_high_yield_property_at_low_rate():
    state = _make_state(rate=0.05)
    # rent=1200/month → annual=14400 → yield=14400/200000=7.2% > 6%
    available = [_prop("px", 200_000, 1_200)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    state.properties = available
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "buy"
    assert pid == "px"
    assert ltv == 0.0   # yield AI buys cash (no leverage)


def test_yield_ai_holds_when_rate_high():
    state = _make_state(rate=0.08)
    available = [_prop("px", 200_000, 1_200)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "hold"


def test_yield_ai_holds_when_yield_too_low():
    state = _make_state(rate=0.05)
    # rent=500/month → annual=6000 → yield=6000/200000=3% < 6%
    available = [_prop("px", 200_000, 500)]
    actor = ActorState(id="ai1", name="Conservative AI", cash=300_000,
                       risk_appetite=0.3, strategy="yield")
    state.actors = {"ai1": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "hold"


def test_leverage_ai_buys_with_75pct_ltv_at_low_rate():
    state = _make_state(rate=0.04)
    available = [_prop("px", 200_000, 800)]
    actor = ActorState(id="ai2", name="Aggressive AI", cash=100_000,
                       risk_appetite=0.9, strategy="leverage", portfolio=[])
    state.actors = {"ai2": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, available)
    assert action == "buy"
    assert ltv == pytest.approx(0.75)


def test_leverage_ai_sells_on_rate_spike():
    state = _make_state(rate=0.09)
    actor = ActorState(id="ai2", name="Aggressive AI", cash=50_000,
                       risk_appetite=0.9, strategy="leverage", portfolio=["p01"])
    prop_owned = _prop("p01", 300_000, 900)
    state.actors = {"ai2": actor}
    state.properties = [prop_owned]
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, [])
    assert action == "sell"
    assert pid == "p01"


def test_balanced_ai_holds_by_default():
    state = _make_state(rate=0.06)
    actor = ActorState(id="player", name="Player", cash=100_000,
                       risk_appetite=0.5, strategy="balanced")
    state.actors = {"player": actor}
    ai = AIController()
    action, pid, ltv = ai._decide(state, actor, [])
    assert action == "hold"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_ai_strategies.py -v
```
Expected: FAIL — `_decide` returns two values, not three; no strategy logic

- [ ] **Step 3: Rewrite `ai.py`**

```python
YIELD_TARGET   = 0.06   # minimum gross annual yield to buy (yield strategy)
YIELD_MAX_RATE = 0.07   # yield AI holds when BoE rate exceeds this
LEVERAGE_MAX_RATE_BUY  = 0.05   # leverage AI only buys when rate <= this
LEVERAGE_SELL_RATE     = 0.085  # leverage AI sells when rate exceeds this
LTV_LEVERAGE = 0.75


class AIController:
    def step(self, state, tick):
        owned_all = {pid for a in state.actors.values() for pid in a.portfolio}
        available = [p for p in state.properties if p.id not in owned_all]
        events = []
        for actor_id, actor in state.actors.items():
            if actor_id == "player":
                continue
            action, property_id, ltv = self._decide(state, actor, available)
            events.append({
                "type": "ai_action",
                "tick": tick,
                "actor_id": actor_id,
                "action": action,
                "property_id": property_id,
                "ltv": ltv,
                "detail": f"AI {actor.name} [{actor.strategy}]: {action}"
                          + (f" {property_id}" if property_id else ""),
            })
        return events

    def _decide(self, state, actor, available):
        strategy = actor.strategy
        if strategy == "yield":
            return self._decide_yield(state, actor, available)
        if strategy == "leverage":
            return self._decide_leverage(state, actor, available)
        return "hold", None, 0.0

    def _decide_yield(self, state, actor, available):
        rate = state.macro.interest_rate
        if rate > YIELD_MAX_RATE:
            return "hold", None, 0.0
        for prop in available:
            gross_yield = (prop.rent * 12) / prop.current_value
            deposit = prop.current_value  # cash purchase
            if gross_yield >= YIELD_TARGET and actor.cash >= deposit:
                return "buy", prop.id, 0.0
        return "hold", None, 0.0

    def _decide_leverage(self, state, actor, available):
        rate = state.macro.interest_rate
        if rate > LEVERAGE_SELL_RATE and actor.portfolio:
            return "sell", actor.portfolio[0], 0.0
        if rate <= LEVERAGE_MAX_RATE_BUY:
            for prop in available:
                deposit = prop.current_value * (1 - LTV_LEVERAGE)
                if actor.cash >= deposit * 1.1:   # 10% buffer for SDLT
                    return "buy", prop.id, LTV_LEVERAGE
        return "hold", None, 0.0
```

- [ ] **Step 4: Update `_execute_action` call site in `kernel.py`**

The `_execute_action` already reads `ltv` from the event dict (added in Task 3). Confirm the AI event now includes `ltv` — it does from the rewritten `ai.py` above. No further kernel change needed.

- [ ] **Step 5: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add ai.py tests/test_ai_strategies.py
git commit -m "feat: strategy-aware AI — yield and leverage decision logic"
```

---

## Task 5: EPC Regulatory Shock and Forced Compliance

Add `epc_mandate` event to `shocks.py` (fires when cumulative ticks cross a threshold representing 2028 regulatory deadline). In the kernel tick loop, when `epc_mandate` fires, issue compliance warnings; two ticks later force-sell non-upgraded properties at 15% discount.

**Files:**
- Modify: `shocks.py`
- Modify: `kernel.py` — handle EPC mandate in tick loop
- Modify: `property_model.py` — already handles EPC band via upgrade action in Task 3
- Create: `tests/test_epc.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_epc.py
import pytest
from shocks import detect_events
from kernel import SimulationKernel
from state import Property, ActorState, SimulationState, MacroState


def _entry(year, half, hpi, rate, rent, cpi):
    return (year, half, hpi, rate, rent, cpi)


def test_epc_mandate_fires_at_tick_10():
    # The mandate fires once when tick == EPC_MANDATE_TICK
    k = SimulationKernel(turns=12, turn_delay=0)
    k.run()
    epc_events = [e for e in k.state.event_log if e["type"] == "epc_mandate"]
    assert len(epc_events) == 1
    assert epc_events[0]["tick"] == 10


def test_epc_mandate_warns_non_compliant_properties():
    k = SimulationKernel(turns=12, turn_delay=0)
    k.run()
    warn_events = [e for e in k.state.event_log if e["type"] == "epc_warning"]
    # properties with epc_band >= 4 should have warnings
    non_compliant_ids = {p.id for p in k.state.properties if p.epc_band >= 4}
    warned_ids = {e["property_id"] for e in warn_events}
    assert non_compliant_ids.issubset(warned_ids)


def test_unupgraded_property_force_sold_after_grace_period():
    k = SimulationKernel(turns=14, turn_delay=0)
    # Find which actor owns a non-compliant property at tick 10
    k.run()
    force_events = [e for e in k.state.event_log if e["type"] == "epc_force_sell"]
    # At least one force sell should occur (default properties have band 4-7)
    assert len(force_events) > 0


def test_force_sell_applies_15pct_discount():
    k = SimulationKernel(turns=14, turn_delay=0)
    k.run()
    for e in k.state.event_log:
        if e["type"] == "epc_force_sell":
            assert e["discount"] == pytest.approx(0.15)
            break
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_epc.py -v
```
Expected: FAIL — no `epc_mandate` events in event log

- [ ] **Step 3: Add EPC mandate constant and tracking to `kernel.py`**

At the top of `kernel.py` after `TURN_STATE_PATH`:

```python
EPC_MANDATE_TICK = 10     # fires once; actors have 2 ticks to comply
EPC_GRACE_TICKS  = 2
```

Add `_epc_warned: dict` to `SimulationKernel.__init__` after `self.scoring = ScoringEngine()`:

```python
        self._epc_warned = {}   # property_id -> tick when warning was issued
```

- [ ] **Step 4: Add EPC mandate handling in `kernel.py` `run()` tick loop**

After `tick_events += self.scenario_events.step(self.state, tick)` add:

```python
            # EPC mandate: fire warning at mandate tick, force-sell after grace period
            if tick == EPC_MANDATE_TICK:
                for prop in self.state.properties:
                    if prop.epc_band >= 4:
                        self._epc_warned[prop.id] = tick
                        tick_events.append({
                            "type": "epc_mandate",
                            "tick": tick,
                            "detail": "EPC minimum-C mandate activated",
                        })
                        tick_events.append({
                            "type": "epc_warning",
                            "tick": tick,
                            "property_id": prop.id,
                            "detail": f"{prop.id} (EPC {chr(64 + prop.epc_band)}) must be upgraded within {EPC_GRACE_TICKS} ticks",
                        })

            # Force-sell non-compliant properties after grace period
            for prop in list(self.state.properties):
                warned_at = self._epc_warned.get(prop.id)
                if warned_at and tick == warned_at + EPC_GRACE_TICKS and prop.epc_band >= 4:
                    for actor in self.state.actors.values():
                        if prop.id in actor.portfolio:
                            sale_price = prop.current_value * 0.85
                            agent_fee  = sale_price * 0.015
                            net = sale_price - prop.mortgage_balance - agent_fee
                            actor.cash += max(net, 0.0)
                            actor.total_transaction_costs += agent_fee
                            prop.mortgage_balance = 0.0
                            actor.portfolio.remove(prop.id)
                            tick_events.append({
                                "type": "epc_force_sell",
                                "tick": tick,
                                "property_id": prop.id,
                                "actor_id": actor.id,
                                "discount": 0.15,
                                "detail": f"{prop.id} force-sold at 15% discount — EPC non-compliance",
                            })
                            break
```

- [ ] **Step 5: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add kernel.py tests/test_epc.py
git commit -m "feat: EPC mandate shock, compliance warnings, force-sell at tick 10+grace"
```

---

## Task 6: Player Browser Action Panel

Add a `POST /action` endpoint to the Flask server. `player/choices.py` reads `visualisation/player_action.json` each tick instead of hardcoding hold. The kernel writes available properties and player portfolio state to `turn_state.json`. The dashboard shows a "Your Move" panel with buy/sell/upgrade/hold buttons.

**Files:**
- Modify: `visualisation/dashboard_server.py`
- Modify: `player/choices.py`
- Modify: `kernel.py` — enrich `turn_state.json` with player-facing data
- Modify: `static/dashboard.html` — add action panel
- Create: `tests/test_player_action.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_player_action.py
import json
import os
import tempfile
import pytest
from player.choices import PlayerChoiceEngine
from state import Property, ActorState, SimulationState, MacroState


def _make_state():
    prop = Property(id="px", region="Test", base_value=200_000,
                    current_value=200_000, rent=900.0)
    actor = ActorState(id="player", name="Player", cash=250_000,
                       risk_appetite=0.5, portfolio=["p1"])
    owned_prop = Property(id="p1", region="London", base_value=300_000,
                          current_value=300_000, rent=1500.0)
    state = SimulationState()
    state.macro = MacroState()
    state.properties = [prop, owned_prop]
    state.actors = {"player": actor}
    return state


def test_player_defaults_to_hold_when_no_action_file(tmp_path, monkeypatch):
    monkeypatch.setattr("player.choices.ACTION_PATH", str(tmp_path / "action.json"))
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "hold"


def test_player_reads_buy_action_for_current_tick(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "buy"
    assert events[0]["property_id"] == "px"


def test_player_ignores_stale_action(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=2)   # stale — tick doesn't match
    assert events[0]["action"] == "hold"


def test_player_reads_sell_action(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 3, "action": "sell", "property_id": "p1"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    events = engine.step(state, tick=3)
    assert events[0]["action"] == "sell"
    assert events[0]["property_id"] == "p1"


def test_action_file_cleared_after_read(tmp_path, monkeypatch):
    action_path = str(tmp_path / "action.json")
    monkeypatch.setattr("player.choices.ACTION_PATH", action_path)
    with open(action_path, "w") as f:
        json.dump({"tick": 1, "action": "buy", "property_id": "px"}, f)
    state = _make_state()
    engine = PlayerChoiceEngine()
    engine.step(state, tick=1)
    # second call same tick should hold (file cleared)
    events = engine.step(state, tick=1)
    assert events[0]["action"] == "hold"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_player_action.py -v
```
Expected: FAIL — `player.choices` has no `ACTION_PATH`, always holds

- [ ] **Step 3: Rewrite `player/choices.py`**

```python
import json
import os

ACTION_PATH = os.path.join(os.path.dirname(__file__), "..", "visualisation", "player_action.json")


class PlayerChoiceEngine:
    def step(self, state, tick):
        action, property_id = self._read_action(tick)
        return [{
            "type": "player_action",
            "tick": tick,
            "actor_id": "player",
            "action": action,
            "property_id": property_id,
            "ltv": 0.0,
            "detail": f"Player: {action}{' ' + property_id if property_id else ''}",
        }]

    def _read_action(self, tick):
        try:
            with open(ACTION_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("tick") == tick:
                # clear so the same action can't fire twice
                with open(ACTION_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                return data.get("action", "hold"), data.get("property_id")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return "hold", None
```

- [ ] **Step 4: Add `POST /action` to `visualisation/dashboard_server.py`**

```python
import json
import logging
import os
import socket
import threading
from flask import Flask, Response, send_file, request

logging.getLogger("werkzeug").setLevel(logging.ERROR)

_DEFAULT_STATE_PATH  = os.path.join(os.path.dirname(__file__), "turn_state.json")
_DEFAULT_ACTION_PATH = os.path.join(os.path.dirname(__file__), "player_action.json")


def create_app(state_path=None, action_path=None):
    if state_path is None:
        state_path = _DEFAULT_STATE_PATH
    if action_path is None:
        action_path = _DEFAULT_ACTION_PATH

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

    @app.route("/action", methods=["POST"])
    def action():
        data = request.get_json(silent=True) or {}
        with open(action_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return Response('{"ok":true}', mimetype="application/json",
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

- [ ] **Step 5: Enrich `turn_state.json` with player-facing data in `kernel.py`**

In `_write_turn_state`, inside the `data = { ... }` dict, add `"player_state"` key:

```python
        player = self.state.actors.get("player")
        prop_map = {p.id: p for p in self.state.properties}
        owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}

        player_portfolio = []
        if player:
            for pid in player.portfolio:
                p = prop_map.get(pid)
                if p:
                    player_portfolio.append({
                        "id": p.id, "region": p.region,
                        "value": round(p.current_value, 0),
                        "rent_monthly": round(p.rent, 0),
                        "epc_band": p.epc_band,
                        "epc_label": chr(64 + p.epc_band),
                        "mortgage": round(p.mortgage_balance, 0),
                        "archetype": p.archetype,
                    })

        available_props = []
        for p in self.state.properties:
            if p.id not in owned_all:
                from kernel import _calculate_sdlt
                gross_yield = round((p.rent * 12) / p.current_value * 100, 1)
                affordable = player and player.cash >= (p.current_value + _calculate_sdlt(p.current_value))
                available_props.append({
                    "id": p.id, "region": p.region,
                    "value": round(p.current_value, 0),
                    "sdlt": round(_calculate_sdlt(p.current_value), 0),
                    "gross_yield_pct": gross_yield,
                    "epc_band": p.epc_band,
                    "epc_label": chr(64 + p.epc_band),
                    "archetype": p.archetype,
                    "affordable": affordable,
                })
```

Add to `data` dict:

```python
            "player_state": {
                "cash": round(player.cash, 0) if player else 0,
                "portfolio": player_portfolio,
                "available": available_props,
                "tick": self.state.tick,
            },
```

- [ ] **Step 6: Add "Your Move" action panel to `static/dashboard.html`**

Add these CSS styles inside the existing `<style>` block before `</style>`:

```css
  .action-panel { display: flex; flex-direction: column; gap: 8px; }
  .action-panel h3 { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 4px; }
  .prop-row { font-size: 11px; color: #ccc; padding: 5px 0; border-bottom: 1px solid #2a3f50; display: flex; justify-content: space-between; align-items: center; }
  .prop-row:last-child { border-bottom: none; }
  .epc-badge { font-size: 10px; padding: 1px 5px; border-radius: 3px; font-weight: 700; }
  .epc-a { background:#1a3a1a; color:#4caf50; } .epc-b { background:#1a3020; color:#66bb6a; }
  .epc-c { background:#2a3a1a; color:#aed581; } .epc-d { background:#3a3a1a; color:#ffeb3b; }
  .epc-e { background:#3a2a1a; color:#ffa726; } .epc-f { background:#3a1a1a; color:#ef5350; }
  .epc-g { background:#2a1a1a; color:#b71c1c; }
  .act-btn { font-size: 10px; padding: 3px 8px; border-radius: 3px; border: none; cursor: pointer; margin-left: 4px; }
  .btn-buy  { background:#1e3a1e; color:#4caf50; border:1px solid #4caf50; }
  .btn-sell { background:#3a1a1a; color:#ef5350; border:1px solid #ef5350; }
  .btn-upgrade { background:#3a2a1a; color:#ffa726; border:1px solid #ffa726; }
  .btn-hold { background:#1a2733; color:#888; border:1px solid #555; }
  .action-status { font-size: 11px; color: #4caf50; min-height: 16px; }
```

Add the action panel div inside `.sidebar` after the event feed panel (after line `</div>` closing `style="flex:1;overflow:auto;"`):

```html
      <div class="panel">
        <div class="action-panel">
          <h3>Your Move</h3>
          <div id="action-status" class="action-status"></div>
          <div style="font-size:10px;color:#888;margin-bottom:4px;">YOUR PROPERTIES</div>
          <div id="player-portfolio"></div>
          <div style="font-size:10px;color:#888;margin:6px 0 4px;">AVAILABLE TO BUY</div>
          <div id="available-props"></div>
          <div style="margin-top:8px;">
            <button class="act-btn btn-hold" onclick="submitAction('hold',null)">Hold this turn</button>
          </div>
        </div>
      </div>
```

Add this JavaScript before the closing `</script>`:

```javascript
function epcClass(band) {
  return ['','epc-a','epc-b','epc-c','epc-d','epc-e','epc-f','epc-g'][band] || 'epc-g';
}

function submitAction(action, propertyId) {
  const tick = window._currentTick || 0;
  fetch('/action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({tick, action, property_id: propertyId})
  }).then(() => {
    const label = action === 'hold' ? 'Holding this turn' :
                  `${action.charAt(0).toUpperCase()+action.slice(1)}: ${propertyId}`;
    document.getElementById('action-status').textContent = '✓ ' + label;
    setTimeout(() => { document.getElementById('action-status').textContent = ''; }, 3000);
  });
}

function renderPlayerPanel(ps) {
  if (!ps) return;
  window._currentTick = ps.tick;

  const portfolio = document.getElementById('player-portfolio');
  portfolio.innerHTML = (ps.portfolio || []).map(p => `
    <div class="prop-row">
      <span>${p.region} <span class="epc-badge ${epcClass(p.epc_band)}">${p.epc_label}</span></span>
      <span>
        £${(p.value/1000).toFixed(0)}k
        <button class="act-btn btn-sell" onclick="submitAction('sell','${p.id}')">Sell</button>
        ${p.epc_band >= 4 ? `<button class="act-btn btn-upgrade" onclick="submitAction('upgrade','${p.id}')">Upgrade EPC</button>` : ''}
      </span>
    </div>`).join('') || '<div style="font-size:11px;color:#555;">No properties owned</div>';

  const avail = document.getElementById('available-props');
  avail.innerHTML = (ps.available || []).map(p => `
    <div class="prop-row" style="${!p.affordable ? 'opacity:0.45' : ''}">
      <span>${p.region} <span class="epc-badge ${epcClass(p.epc_band)}">${p.epc_label}</span>
        <span style="color:#888;font-size:10px;"> ${p.gross_yield_pct}%</span></span>
      <span>£${(p.value/1000).toFixed(0)}k
        ${p.affordable ? `<button class="act-btn btn-buy" onclick="submitAction('buy','${p.id}')">Buy</button>` : ''}
      </span>
    </div>`).join('') || '<div style="font-size:11px;color:#555;">All properties owned</div>';
}
```

In the existing `render(data)` function, add a call to `renderPlayerPanel` at the end:

```javascript
  renderPlayerPanel(data.player_state);
```

- [ ] **Step 7: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add player/choices.py visualisation/dashboard_server.py kernel.py static/dashboard.html tests/test_player_action.py
git commit -m "feat: player browser action panel — buy/sell/upgrade via dashboard"
```

---

## Task 7: Risk-Adjusted Scoring and End-Game Breakdown

Extend `ScoringEngine` to compute a composite risk score per actor, risk-adjusted return, and income/capital split. Pass extended scores through `turn_state.json` and show breakdown in the dashboard's era banner at game end.

**Files:**
- Modify: `scoring.py`
- Modify: `kernel.py` — pass extended leaderboard to `turn_state.json`
- Modify: `static/dashboard.html` — richer era banner
- Create: `tests/test_scoring_extended.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scoring_extended.py
import pytest
from scoring import ScoringEngine
from state import Property, ActorState, SimulationState, MacroState


def _make_state():
    p1 = Property(id="p1", region="London", base_value=300_000,
                  current_value=330_000, rent=1_500.0, epc_band=3,
                  mortgage_balance=0.0)
    p2 = Property(id="p2", region="Leeds",  base_value=150_000,
                  current_value=140_000, rent=700.0,  epc_band=5,
                  mortgage_balance=50_000.0)
    actor = ActorState(id="a1", name="Inv", cash=80_000.0, risk_appetite=0.5,
                       portfolio=["p1", "p2"],
                       total_rent_received=20_000.0,
                       total_mortgage_paid=8_000.0,
                       total_transaction_costs=5_000.0,
                       initial_wealth=500_000.0)
    state = SimulationState()
    state.macro = MacroState()
    state.properties = [p1, p2]
    state.actors = {"a1": actor}
    return state, actor


def test_risk_score_between_0_and_100():
    state, actor = _make_state()
    eng = ScoringEngine()
    score = eng.compute_risk_score(actor, state.properties)
    assert 0 <= score <= 100


def test_high_epc_and_high_ltv_gives_higher_risk():
    state, actor = _make_state()
    eng = ScoringEngine()
    # baseline
    base = eng.compute_risk_score(actor, state.properties)
    # worsen EPC and increase mortgage
    state.properties[0].epc_band = 7
    state.properties[1].mortgage_balance = 140_000
    worse = eng.compute_risk_score(actor, state.properties)
    assert worse > base


def test_leaderboard_includes_risk_and_return_fields():
    state, _ = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    assert "risk_score" in lb[0]
    assert "income_return" in lb[0]
    assert "capital_return" in lb[0]
    assert "risk_adjusted_return" in lb[0]


def test_income_return_matches_rent_received():
    state, actor = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    assert lb[0]["income_return"] == pytest.approx(actor.total_rent_received)


def test_capital_return_is_portfolio_gain():
    state, actor = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    # p1 gained 30k, p2 lost 10k, net = 20k
    assert lb[0]["capital_return"] == pytest.approx(20_000, rel=1e-3)


def test_empty_portfolio_risk_score_is_neutral():
    state, actor = _make_state()
    actor.portfolio = []
    eng = ScoringEngine()
    score = eng.compute_risk_score(actor, state.properties)
    assert score == 50.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_scoring_extended.py -v
```
Expected: FAIL — `leaderboard` missing `risk_score`, `income_return`, etc.

- [ ] **Step 3: Rewrite `scoring.py`**

```python
class ScoringEngine:
    def record_rent(self, actor_id, amount):
        pass   # now tracked directly on ActorState.total_rent_received

    def compute_risk_score(self, actor, properties):
        prop_map = {p.id: p for p in properties}
        held = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
        if not held:
            return 50.0

        total_value = sum(p.current_value for p in held)

        # Asset risk: average EPC band (1=A best, 7=G worst)
        avg_epc = sum(p.epc_band for p in held) / len(held)
        asset_risk = (avg_epc - 1) / 6 * 100

        # Financial risk: portfolio LTV
        total_mortgage = sum(p.mortgage_balance for p in held)
        ltv = total_mortgage / total_value if total_value > 0 else 0.0
        financial_risk = min(ltv / 0.85, 1.0) * 100

        # Concentration risk: fraction of value in single region
        region_values = {}
        for p in held:
            region_values[p.region] = region_values.get(p.region, 0) + p.current_value
        max_concentration = max(region_values.values()) / total_value if total_value > 0 else 1.0
        concentration_risk = max_concentration * 100

        return round(
            0.40 * asset_risk +
            0.40 * financial_risk +
            0.20 * concentration_risk,
            1,
        )

    def compute_scores(self, state):
        prop_map = {p.id: p for p in state.properties}
        scores = {}
        for actor_id, actor in state.actors.items():
            current_pv = sum(
                prop_map[pid].current_value
                for pid in actor.portfolio if pid in prop_map
            )
            initial_pv = actor.initial_wealth - actor.cash   # rough initial portfolio value
            capital_return = (current_pv - initial_pv) if actor.initial_wealth > 0 else 0.0
            income_return  = actor.total_rent_received
            total_return   = current_pv + actor.cash - actor.initial_wealth
            risk_score     = self.compute_risk_score(actor, state.properties)
            # Risk-adjusted: total return penalised by risk (higher risk = lower score)
            risk_factor = max(0.1, 1.0 - risk_score / 200)
            risk_adj    = round(total_return * risk_factor, 0)

            scores[actor_id] = {
                "actor_id":           actor_id,
                "name":               actor.name,
                "portfolio_value":    round(current_pv, 0),
                "cash":               round(actor.cash, 0),
                "income_return":      round(income_return, 0),
                "capital_return":     round(capital_return, 0),
                "total_return":       round(total_return, 0),
                "risk_score":         risk_score,
                "risk_adjusted_return": risk_adj,
                "final_score":        risk_adj,
            }
        return scores

    def leaderboard(self, state):
        scores = self.compute_scores(state)
        return sorted(scores.values(), key=lambda s: s["final_score"], reverse=True)
```

- [ ] **Step 4: Update `scoring.record_rent` call sites in `kernel.py`**

Search for `self.scoring.record_rent` in `kernel.py` and remove any calls — rent is now tracked on `actor.total_rent_received` directly in `actors.py`. If no calls exist, skip.

- [ ] **Step 5: Pass extended leaderboard into `turn_state.json` in `kernel.py`**

The `_write_turn_state` already writes `leaderboard` at game end via the `run()` return value. Ensure the final `turn_state.json` includes the leaderboard by adding it to `data` in `_write_turn_state` when `is_final=True`:

```python
        if is_final:
            data["leaderboard"] = self.scoring.leaderboard(self.state)
```

- [ ] **Step 6: Update `static/dashboard.html` era banner to show scoring breakdown**

Replace the era banner `<div id="era-banner">` section with:

```html
  <div id="era-banner">
    <h2 id="era-title"></h2>
    <p id="era-sub" style="margin-bottom:12px;"></p>
    <div id="leaderboard-table" style="text-align:left;max-width:600px;margin:0 auto;"></div>
  </div>
```

In the JavaScript `render(data)` function, update the era banner block:

```javascript
  if (data.era_label && !document.getElementById('era-banner').style.display) {
    document.getElementById('era-banner').style.display = 'flex';
    document.getElementById('era-title').textContent = data.era_label;
    document.getElementById('era-sub').textContent = 'Game complete — final standings';
    if (data.leaderboard) {
      const rows = data.leaderboard.map((e, i) => `
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;gap:6px;
                    padding:6px 0;border-bottom:1px solid #2a3f50;font-size:11px;color:#ccc;">
          <span style="color:#ecad0a;">${i+1}. ${e.name}</span>
          <span>Income £${(e.income_return/1000).toFixed(0)}k</span>
          <span>Capital £${(e.capital_return/1000).toFixed(0)}k</span>
          <span>Risk ${e.risk_score}</span>
          <span style="color:#4caf50;">Score £${(e.risk_adjusted_return/1000).toFixed(0)}k</span>
        </div>`).join('');
      document.getElementById('leaderboard-table').innerHTML =
        `<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;gap:6px;
                     padding:4px 0;font-size:10px;color:#555;text-transform:uppercase;">
           <span>Player</span><span>Income</span><span>Capital</span><span>Risk</span><span>Score</span>
         </div>` + rows;
    }
  }
```

- [ ] **Step 7: Run all tests**

```
pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 8: Run full smoke test to confirm game completes end-to-end**

```
pytest tests/test_smoke.py -v
```
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add scoring.py kernel.py static/dashboard.html tests/test_scoring_extended.py
git commit -m "feat: risk-adjusted scoring with income/capital split and end-game breakdown"
```

---

## Self-Review

**Spec coverage check:**

| Enhancement | Task | Covered? |
|---|---|---|
| Property archetypes + EPC bands | Task 1 | ✓ |
| Mortgage / leverage layer | Task 2 | ✓ |
| Transaction costs (SDLT, agent fees, void, capex) | Task 3 | ✓ |
| Strategy-aware AI | Task 4 | ✓ |
| EPC regulatory shock → forced sale | Task 5 | ✓ |
| Player browser action panel | Task 6 | ✓ |
| Risk-adjusted scoring | Task 7 | ✓ |

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency check:**
- `Property.epc_band` defined in Task 1 (int), used in Tasks 3, 5, 6, 7 — consistent
- `ActorState.strategy` defined in Task 1 (str), used in Task 4 — consistent
- `ActorState.total_rent_received` defined in Task 1 (float), incremented in Task 2 (`actors.py`), read in Task 7 (`scoring.py`) — consistent
- `_calculate_sdlt(price)` defined in Task 3, imported in Task 6 (`kernel.py _write_turn_state`) — consistent
- `_epc_upgrade_cost(epc_band)` defined in Task 3, used in Task 3 `_execute_action` — consistent
- `AIController._decide` returns `(action, pid, ltv)` in Task 4; `_execute_action` reads `event.get("ltv", 0.0)` added in Task 3 — consistent
- `EPC_MANDATE_TICK = 10` in Task 5; test asserts `tick == 10` — consistent
