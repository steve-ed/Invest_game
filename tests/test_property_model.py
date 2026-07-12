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
    state.macro.rent_growth = 0.12  # 12% annual -> 6% semi-annual
    model = PropertyModel()
    model.update(state)
    assert abs(state.properties[0].rent - 1590.0) < 0.01


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
