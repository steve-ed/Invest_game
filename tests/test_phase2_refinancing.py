import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app


def _make_gs():
    return web_app.init_game_state(total_ticks=40)


def _gs_with_mortgage(rate_type='variable'):
    gs = _make_gs()
    prop = {'id': 'P-99', 'region': 'North', 'value': 100000, 'rent': 500,
            'epc_compliant': True}
    gs['player']['portfolio'].append(prop)
    rate = gs['macro']['rate']
    mortgage = {
        'prop_id': 'P-99',
        'loan': 50000,
        'rate_type': rate_type,
        'rate': rate,
        'fixed_rate': rate if rate_type != 'variable' else None,
        'fix_expires_tick': gs['tick'] + 8 if rate_type == 'fixed_2yr' else None,
        'monthly_payment': round((50000 * rate / 100) / 12, 2),
    }
    gs['player']['mortgages'].append(mortgage)
    return gs


def test_refinance_cooldown_initialized_to_zero():
    gs = _make_gs()
    assert gs['refinance_cooldown'] == 0


def test_advance_tick_decrements_cooldown():
    gs = _make_gs()
    gs['refinance_cooldown'] = 3
    web_app.advance_tick(gs)
    assert gs['refinance_cooldown'] == 2


def test_advance_tick_does_not_go_below_zero():
    gs = _make_gs()
    gs['refinance_cooldown'] = 0
    web_app.advance_tick(gs)
    assert gs['refinance_cooldown'] == 0


def test_remortgage_blocked_when_cooldown_active():
    gs = _gs_with_mortgage()
    gs['refinance_cooldown'] = 3
    cash_before = gs['player']['cash']
    web_app.apply_player_action(gs, 'remortgage', 'P-99', None,
                                ltv=0.75, rate_type='fixed_2yr')
    assert gs['refinance_cooldown'] == 3        # unchanged
    assert gs['player']['cash'] == cash_before  # no change


def test_remortgage_sets_cooldown_to_five():
    gs = _gs_with_mortgage()
    assert gs['refinance_cooldown'] == 0
    web_app.apply_player_action(gs, 'remortgage', 'P-99', None,
                                ltv=0.5, rate_type='fixed_2yr')
    assert gs['refinance_cooldown'] == 5


def test_remortgage_allows_rate_switch_without_equity_release():
    # Existing loan = 50000 at 50% LTV → same LTV → cash_released = 0
    gs = _gs_with_mortgage(rate_type='variable')
    cash_before = gs['player']['cash']
    web_app.apply_player_action(gs, 'remortgage', 'P-99', None,
                                ltv=0.5, rate_type='fixed_2yr')
    mortgage = gs['player']['mortgages'][0]
    assert mortgage['rate_type'] == 'fixed_2yr'
    assert gs['player']['cash'] == cash_before   # no cash change
