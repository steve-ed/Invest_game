import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app


def _make_gs():
    return web_app.init_game_state(total_ticks=40)


def _portfolio(region, count, value=100000):
    return [{'id': f'P-{i}', 'region': region, 'value': value, 'rent': 500, 'epc_compliant': True}
            for i in range(count)]


def test_no_penalty_with_three_properties_in_region():
    assert web_app.concentration_penalty(_portfolio('North', 3)) == 0


def test_penalty_with_four_properties_same_region():
    # excess = 1, avg_value = 100000 → penalty = 1 * 100000 * 0.05 = 5000
    assert web_app.concentration_penalty(_portfolio('North', 4)) == 5000


def test_penalty_with_five_properties_same_region():
    # excess = 2 → penalty = 2 * 100000 * 0.05 = 10000
    assert web_app.concentration_penalty(_portfolio('North', 5)) == 10000


def test_penalty_accumulates_across_regions():
    # 4 North (5000) + 4 South (5000) = 10000
    portfolio = _portfolio('North', 4) + _portfolio('South', 4)
    assert web_app.concentration_penalty(portfolio) == 10000


def test_empty_portfolio_no_penalty():
    assert web_app.concentration_penalty([]) == 0


def test_player_score_deducts_concentration_penalty():
    gs = _make_gs()
    # Clear portfolio and add 4 same-region props
    gs['player']['portfolio'] = _portfolio('North', 4, value=100000)
    gs['player']['mortgages'] = []
    score = web_app.player_score(gs)
    # Penalty = 5000; score must be less than it would be without it
    # Compute what score would be without penalty via score_for_archetype with pen=0
    portfolio_val = 400000
    cash = gs['player']['cash']
    score_no_pen = web_app.score_for_archetype(
        gs.get('archetype', 'balanced'), portfolio_val, cash, 0, 0, concentration_pen=0
    )
    assert score == score_no_pen - 5000
