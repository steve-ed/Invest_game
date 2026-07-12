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


def test_macro_snapshot_fields():
    from state import MacroSnapshot
    snap = MacroSnapshot(
        tick=3,
        scenario="baseline",
        price_index=101.5,
        interest_rate=0.052,
        rent_growth=0.03,
        events=[{"type": "shock"}],
    )
    assert snap.tick == 3
    assert snap.scenario == "baseline"
    assert snap.events == [{"type": "shock"}]


def test_simulation_state_has_macro_history():
    s = SimulationState()
    assert s.macro_history == []


def test_simulation_state_has_last_ai_actions():
    s = SimulationState()
    assert s.last_ai_actions == {}


def test_simulation_state_has_event_log():
    s = SimulationState()
    assert s.event_log == []


def test_simulation_state_has_era_fields():
    s = SimulationState()
    assert s.start_year == 0
    assert s.start_half == 1
    assert s.era_label == ""


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
