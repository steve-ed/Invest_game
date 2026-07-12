import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
from unittest.mock import patch
import app as web_app


def _make_gs():
    return web_app.init_game_state(total_ticks=40)


def _prop(rent, value=100000):
    return {'id': 'P-99', 'region': 'North', 'value': value, 'rent': rent,
            'epc_compliant': True}


def test_void_chance_at_three_percent_yield_is_zero():
    # 500 * 12 / 200000 * 100 = 3.0%
    assert web_app._void_chance({'value': 200000, 'rent': 500}) == 0.0


def test_void_chance_below_three_percent_is_zero():
    # 1% yield
    assert web_app._void_chance({'value': 1000000, 'rent': 833}) == 0.0


def test_void_chance_at_six_percent_yield():
    # 500 * 12 / 100000 * 100 = 6% → (6 - 3) / 100 = 0.03
    assert abs(web_app._void_chance({'value': 100000, 'rent': 500}) - 0.03) < 0.001


def test_void_chance_at_ten_percent_yield():
    # 833 * 12 / 100000 * 100 ≈ 10% → (10 - 3) / 100 = 0.07
    assert abs(web_app._void_chance({'value': 100000, 'rent': 833}) - 0.07) < 0.005


def test_apply_void_risk_sets_vacant_when_random_fires():
    gs = _make_gs()
    prop = _prop(rent=833)   # ~10% yield, void_chance ≈ 0.07
    gs['player']['portfolio'] = [prop]
    gs['player']['mortgages'] = []
    # random() returns 0.0 < 0.07 → property goes vacant
    with patch('random.random', return_value=0.0):
        web_app._apply_void_risk(gs)
    assert prop['vacant'] is True
    assert any('P-99' in n and 'vacant' in n for n in gs['news'])


def test_apply_void_risk_zero_chance_never_vacant():
    gs = _make_gs()
    prop = _prop(rent=500, value=200000)   # 3% yield, void_chance = 0
    gs['player']['portfolio'] = [prop]
    gs['player']['mortgages'] = []
    with patch('random.random', return_value=0.0):
        web_app._apply_void_risk(gs)
    assert not prop.get('vacant', False)


def test_vacant_property_earns_zero_rent_in_advance_tick():
    gs = _make_gs()
    prop = _prop(rent=833)   # ~10% yield
    gs['player']['portfolio'] = [prop]
    gs['player']['mortgages'] = []
    cash_before = gs['player']['cash']
    # random() = 0.0 → property goes vacant → zero rent
    with patch('random.random', return_value=0.0):
        web_app.advance_tick(gs)
    # 833 * 3 = 2499 would have been added if let
    cash_delta = gs['player']['cash'] - cash_before
    assert cash_delta < 833 * 3, f"Expected no rent from vacant, got delta={cash_delta}"


def test_property_unletts_next_turn():
    gs = _make_gs()
    prop = _prop(rent=833)
    gs['player']['portfolio'] = [prop]
    gs['player']['mortgages'] = []
    # First tick: always vacant
    with patch('random.random', return_value=0.0):
        web_app.advance_tick(gs)
    assert prop.get('vacant') is True
    # Second tick: never vacant (random returns 1.0)
    with patch('random.random', return_value=1.0):
        web_app.advance_tick(gs)
    assert not prop.get('vacant', False)
