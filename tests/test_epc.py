import pytest
from kernel import SimulationKernel


def test_epc_mandate_fires_at_tick_10():
    k = SimulationKernel(turns=12, turn_delay=0)
    k.run()
    epc_events = [e for e in k.state.event_log if e["type"] == "epc_mandate"]
    assert len(epc_events) >= 1
    assert epc_events[0]["tick"] == 10


def test_epc_mandate_warns_non_compliant_properties():
    k = SimulationKernel(turns=12, turn_delay=0)
    k.run()
    warn_events = [e for e in k.state.event_log if e["type"] == "epc_warning"]
    non_compliant_ids = {p.id for p in k.state.properties if p.epc_band >= 4}
    warned_ids = {e["property_id"] for e in warn_events}
    assert non_compliant_ids.issubset(warned_ids)


def test_unupgraded_property_force_sold_after_grace_period():
    k = SimulationKernel(turns=14, turn_delay=0)
    k.run()
    force_events = [e for e in k.state.event_log if e["type"] == "epc_force_sell"]
    assert len(force_events) > 0


def test_force_sell_applies_15pct_discount():
    k = SimulationKernel(turns=14, turn_delay=0)
    k.run()
    for e in k.state.event_log:
        if e["type"] == "epc_force_sell":
            assert e["discount"] == pytest.approx(0.15)
            break
