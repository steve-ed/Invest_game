from shocks import detect_events

# UK_MACRO tuple format: (year, half, price_index, rate, rent_growth, cpi)
ENTRY_A = (1987, 1, 152.0, 8.5, 5.0, 3.0)
ENTRY_B = (1987, 2, 171.0, 8.5, 5.0, 3.0)   # big price surge
ENTRY_C = (1989, 2, 213.0, 15.0, 6.0, 7.5)  # big rate hike
ENTRY_D = (1992, 1, 177.0, 6.0, 3.5, 4.0)   # big rate cut
ENTRY_E = (1991, 1, 190.0, 12.0, 3.0, 6.0)  # big price fall from C
ENTRY_F = (1993, 1, 168.0, 6.0, 2.0, 2.5)   # rent squeeze


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
    stable_a = (1995, 1, 181.0, 6.5, 3.5, 2.5)
    stable_b = (1995, 2, 182.0, 6.5, 3.5, 2.5)
    events = detect_events(stable_a, stable_b, tick=3)
    assert events == []


def test_rate_rise_fires_when_rate_rises_between_0_5_and_1_5():
    # rate goes from 6.0 to 7.0 — delta = +1.0, should fire rate_rise not rate_shock_up
    prev = (1996, 1, 187.0, 6.0, 4.0, 2.5)
    curr = (1996, 2, 194.0, 7.0, 4.0, 2.5)
    events = detect_events(prev, curr, tick=4)
    types = [e["type"] for e in events]
    assert "rate_rise" in types
    assert "rate_shock_up" not in types


def test_rate_cut_fires_when_rate_falls_between_0_5_and_1_5():
    # rate goes from 7.0 to 6.0 — delta = -1.0, should fire rate_cut not rate_shock_down
    prev = (1997, 2, 219.0, 7.0, 4.5, 2.5)
    curr = (1998, 1, 232.0, 6.0, 4.5, 2.5)
    events = detect_events(prev, curr, tick=5)
    types = [e["type"] for e in events]
    assert "rate_cut" in types
    assert "rate_shock_down" not in types


def test_rent_surge_fires_when_rent_growth_rises_over_2():
    # rent_growth goes from 1.0 to 4.0 — delta = +3.0
    prev = (2021, 2, 877.0, 0.25, 1.0, 2.5)
    curr = (2022, 1, 903.0, 1.0,  4.0, 2.5)
    events = detect_events(prev, curr, tick=9)
    types = [e["type"] for e in events]
    assert "rent_surge" in types
