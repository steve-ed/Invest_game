import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app
from unittest.mock import patch


def _make_gs(total_ticks=40):
    return web_app.init_game_state(total_ticks=total_ticks)


def test_rent_income_collected_for_3_months():
    gs = _make_gs()
    player = gs['player']
    monthly_rent = sum(p['rent'] for p in player['portfolio'])
    cash_before = player['cash']
    mortgages_before = sum(m['monthly_payment'] for m in player.get('mortgages', []))
    with patch('random.random', return_value=1.0):
        web_app.advance_tick(gs)
    gross_rent_3m = monthly_rent * 3
    rent_income = int(gross_rent_3m * (1 - web_app.MGMT_COST_RATE))
    expected_net = rent_income - mortgages_before * 3
    actual_net = player['cash'] - cash_before
    assert abs(actual_net - expected_net) < 500, (
        f"Expected net ~{expected_net}, got {actual_net}"
    )


def test_rent_income_not_collected_for_6_months():
    gs = _make_gs()
    player = gs['player']
    monthly_rent = sum(p['rent'] for p in player['portfolio'])
    cash_before = player['cash']
    mortgages_before = sum(m['monthly_payment'] for m in player.get('mortgages', []))
    with patch('random.random', return_value=1.0):
        web_app.advance_tick(gs)
    six_month_net = monthly_rent * 6 - mortgages_before * 6
    actual_net = player['cash'] - cash_before
    assert abs(actual_net - six_month_net) > 100, (
        "Cash change matched 6-month calculation — period multiplier not updated"
    )


def test_init_game_state_uses_quarterly_slice():
    # Quarterly slices contain entries with period=4 (Q4); semi-annual slices never do
    gs = _make_gs(total_ticks=40)
    assert gs['total_ticks'] == 40
    has_q4 = any(entry[1] == 4 for entry in gs['macro_slice'])
    assert has_q4, "No Q4 entries found — macro_slice is semi-annual not quarterly"


def test_init_game_state_long_80_ticks():
    gs = _make_gs(total_ticks=80)
    assert gs['total_ticks'] == 80
    assert len(gs['macro_slice']) >= 80
    has_q4 = any(entry[1] == 4 for entry in gs['macro_slice'])
    assert has_q4, "No Q4 entries found — macro_slice is semi-annual not quarterly"


def test_london_grows_faster_than_north_in_boom_era():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
    import uk_macro_history as hist_mod

    gs = _make_gs(total_ticks=40)
    # Inject boom-era quarterly slice (1999 Q1 — known London outperformance)
    slc = hist_mod.get_quarterly_slice(1999, 1, 41)
    gs['macro_slice'] = slc
    gs['price_scale'] = 100.0 / slc[0][2]
    gs['real_start_year'] = 1999

    london_prop = {'id': 'TEST-L', 'region': 'London', 'value': 200000, 'rent': 1000, 'epc_compliant': True}
    north_prop  = {'id': 'TEST-N', 'region': 'North',  'value': 200000, 'rent': 1000, 'epc_compliant': True}
    gs['player']['portfolio'].extend([london_prop, north_prop])

    web_app.advance_tick(gs)

    london_val = next(p['value'] for p in gs['player']['portfolio'] if p['id'] == 'TEST-L')
    north_val  = next(p['value'] for p in gs['player']['portfolio'] if p['id'] == 'TEST-N')
    assert london_val > north_val, (
        f"London ({london_val}) should exceed North ({north_val}) in 1999 boom era"
    )
