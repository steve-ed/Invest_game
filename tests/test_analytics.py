import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app
from unittest.mock import patch


def _make_gs():
    return web_app.init_game_state(total_ticks=40)


def test_starting_player_portfolio_has_purchase_price():
    gs = _make_gs()
    for p in gs['player']['portfolio']:
        assert 'purchase_price' in p, f"Property {p['id']} missing purchase_price"
        assert p['purchase_price'] == p['value']


def test_starting_ai_portfolio_has_purchase_price():
    gs = _make_gs()
    for ai in gs['ai']:
        for p in ai['portfolio']:
            assert 'purchase_price' in p, f"AI {ai['name']} property {p['id']} missing purchase_price"
            assert p['purchase_price'] == p['value']


def test_player_buy_stamps_purchase_price():
    gs = _make_gs()
    market = gs['market']
    prop = next(p for p in market if not p.get('auction'))
    prop_id = prop['id']
    prop_value = prop['value']
    web_app.apply_player_action(gs, 'buy', prop_id, None, ltv=0.75, rate_type='variable')
    bought = next((p for p in gs['player']['portfolio'] if p['id'] == prop_id), None)
    assert bought is not None, "Property not found in portfolio after buy"
    assert bought['purchase_price'] == prop_value


def test_ai_buy_stamps_purchase_price():
    gs = _make_gs()
    gs['macro']['rate'] = 3.0
    ai = next(a for a in gs['ai'] if a['name'] == 'Mr Max Lever')
    ai['cash'] = 500_000
    market_before = [p['id'] for p in gs['market']]
    with patch('random.random', return_value=1.0):
        web_app.apply_ai_actions(gs)
    bought_props = [p for p in ai['portfolio'] if p['id'] in market_before]
    for p in bought_props:
        assert 'purchase_price' in p, f"AI bought property {p['id']} missing purchase_price"
