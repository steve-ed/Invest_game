import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app


def _gs_with_prop(value=100000, rent=500):
    gs = web_app.init_game_state(total_ticks=40)
    prop = {'id': 'P-TEST', 'region': 'North', 'value': value, 'rent': rent,
            'epc_compliant': True}
    gs['player']['portfolio'].append(prop)
    gs['player']['mortgages'] = []
    return gs, prop


def test_renovation_increases_value_by_eight_percent():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert prop['value'] == int(100000 * 1.08)


def test_renovation_increases_rent_by_fifteen_percent():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert prop['rent'] == int(500 * 1.15)


def test_renovation_costs_ten_percent_of_value():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    cash_before = gs['player']['cash']
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert gs['player']['cash'] == cash_before - int(100000 * 0.10)


def test_renovation_sets_renovated_flag():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert prop.get('renovated') is True


def test_renovation_blocked_if_already_renovated():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    prop['renovated'] = True
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert prop['value'] == 100000  # unchanged


def test_renovation_blocked_if_insufficient_cash():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 5000  # less than 10% of 100000 = 10000
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert not prop.get('renovated', False)
    assert gs['player']['cash'] == 5000  # unchanged


def test_renovation_generates_news_item():
    gs, prop = _gs_with_prop()
    gs['player']['cash'] = 50000
    web_app.apply_player_action(gs, 'renovate', 'P-TEST', None)
    assert any('Renovation' in n or 'P-TEST' in n for n in gs['news'])
