import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app


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
    web_app.apply_ai_actions(gs)
    bought_props = [p for p in ai['portfolio'] if p['id'] in market_before]
    assert len(bought_props) > 0, "Expected Mr Max Lever to buy at least one property"
    for p in bought_props:
        assert 'purchase_price' in p, f"AI bought property {p['id']} missing purchase_price"


def test_compute_analytics_returns_all_actors():
    gs = _make_gs()
    result = web_app.compute_analytics(gs)
    assert 'You' in result
    for ai in gs['ai']:
        assert ai['name'] in result


def test_compute_analytics_gross_yield():
    gs = _make_gs()
    result = web_app.compute_analytics(gs)
    player = gs['player']
    portfolio = player['portfolio']
    assert portfolio, "test requires at least one starting property"
    annual_rent = sum(p['rent'] * 12 for p in portfolio)
    portfolio_value = sum(p['value'] for p in portfolio)
    expected = round(annual_rent / portfolio_value * 100, 1)
    assert result['You']['gross_yield'] == expected


def test_compute_analytics_unrealised():
    gs = _make_gs()
    p = gs['player']['portfolio'][0]
    p['purchase_price'] = p['value']
    p['value'] = p['value'] + 10_000
    result = web_app.compute_analytics(gs)
    assert result['You']['unrealised'] >= 10_000


def test_compute_analytics_refi_headroom():
    gs = _make_gs()
    result = web_app.compute_analytics(gs)
    player = gs['player']
    portfolio_value = sum(p['value'] for p in player['portfolio'])
    total_debt = sum(m['loan'] for m in player.get('mortgages', []))
    expected = portfolio_value * 0.75 - total_debt
    assert abs(result['You']['refi_headrm'] - expected) < 1


def test_compute_analytics_epc_risk_none_when_all_compliant():
    gs = _make_gs()
    for p in gs['player']['portfolio']:
        p['epc_compliant'] = True
    result = web_app.compute_analytics(gs)
    assert result['You']['epc_count'] == 0
    assert result['You']['epc_value'] == 0


def test_compute_analytics_epc_risk_counts_non_compliant():
    gs = _make_gs()
    assert gs['player']['portfolio'], "test requires at least one starting property"
    gs['player']['portfolio'][0]['epc_compliant'] = False
    prop_value = gs['player']['portfolio'][0]['value']
    result = web_app.compute_analytics(gs)
    assert result['You']['epc_count'] == 1
    assert result['You']['epc_value'] == prop_value


def test_compute_analytics_region_conc():
    gs = _make_gs()
    result = web_app.compute_analytics(gs)
    conc = result['You']['region_conc']
    assert 0.0 <= conc <= 100.0


def test_compute_analytics_empty_portfolio():
    gs = _make_gs()
    gs['player']['portfolio'] = []
    gs['player']['mortgages'] = []
    result = web_app.compute_analytics(gs)
    you = result['You']
    assert you['gross_yield'] == 0.0
    assert you['unrealised'] == 0
    assert you['refi_headrm'] == 0.0
    assert you['epc_count'] == 0
    assert you['region_conc'] == 0.0
