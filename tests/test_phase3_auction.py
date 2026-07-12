import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
from unittest.mock import patch
import app as web_app


def _make_gs():
    return web_app.init_game_state(total_ticks=40)


def _auction_prop(value=100000):
    return {'id': 'P-AUC', 'region': 'North', 'value': value, 'rent': 500,
            'epc_compliant': True, 'auction': True}


def test_add_auction_property_sets_auction_flag():
    gs = _make_gs()
    web_app._add_auction_property(gs)
    auction_props = [p for p in gs['market'] if p.get('auction')]
    assert len(auction_props) == 1


def test_add_auction_property_is_below_market_value():
    gs = _make_gs()
    price_factor = gs['macro']['price_index'] / 100.0
    web_app._add_auction_property(gs)
    ap = next(p for p in gs['market'] if p.get('auction'))
    # Must be 15% below comparable, i.e. value < full market value
    # Comparable = _NATIONAL_BASE_VALUE * profile['price_level'] * price_factor
    # Auction = comparable * 0.85
    assert ap['value'] < int(165000 * price_factor * 2.5)  # below even London market value


def test_auction_property_removed_at_next_advance_tick():
    gs = _make_gs()
    web_app._add_auction_property(gs)
    assert any(p.get('auction') for p in gs['market'])
    with patch('random.random', return_value=1.0):
        web_app.advance_tick(gs)
    assert not any(p.get('auction') for p in gs['market'])


def test_auction_added_at_tick_multiples_of_8():
    gs = _make_gs()
    with patch('random.random', return_value=1.0):
        for _ in range(8):
            web_app.advance_tick(gs)
    assert gs['tick'] == 8
    assert any(p.get('auction') for p in gs['market'])


def test_resolve_auction_player_wins_with_highest_bid():
    gs = _make_gs()
    ap = _auction_prop(value=100000)
    gs['market'].append(ap)
    gs['player']['cash'] = 300000
    # aggressive bids int(100000 * 1.05) = 105000; player bids 110000 → player wins
    winner = web_app._resolve_auction(gs, ap, player_bid=110000, ltv=0.0, rate_type='variable')
    assert winner == 'player'
    assert any(p['id'] == 'P-AUC' for p in gs['player']['portfolio'])
    assert not any(p.get('id') == 'P-AUC' for p in gs['market'])


def test_resolve_auction_aggressive_wins_when_player_bids_less():
    gs = _make_gs()
    ap = _auction_prop(value=100000)
    gs['market'].append(ap)
    gs['player']['cash'] = 300000
    # aggressive bids 105000; player bids 50000 → aggressive wins
    winner = web_app._resolve_auction(gs, ap, player_bid=50000, ltv=0.0, rate_type='variable')
    assert winner == 'Aggressive'
    assert not any(p['id'] == 'P-AUC' for p in gs['player']['portfolio'])


def test_resolve_auction_player_wins_on_tie_with_aggressive():
    gs = _make_gs()
    ap = _auction_prop(value=100000)
    gs['market'].append(ap)
    gs['player']['cash'] = 300000
    aggressive_bid = int(100000 * 1.05)  # 105000
    winner = web_app._resolve_auction(gs, ap, player_bid=aggressive_bid, ltv=0.0, rate_type='variable')
    assert winner == 'player'


def test_resolve_auction_player_passes_aggressive_wins():
    gs = _make_gs()
    ap = _auction_prop(value=100000)
    gs['market'].append(ap)
    gs['player']['cash'] = 300000
    winner = web_app._resolve_auction(gs, ap, player_bid=0, ltv=0.0, rate_type='variable')
    assert winner == 'Aggressive'
