"""Run one game, track per-tick wealth for all actors, plot the winner."""

import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui_web'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui_kivy'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))

from app import (init_game_state, advance_tick, apply_player_action,
                 apply_ai_actions, calc_sdlt, current_real_year)

_BUY_RATE_GATE  = 9.0
_SELL_RATE_GATE = 11.5
_BUY_LTV        = 0.75
_REFI_LTV       = 0.70


def _prices_falling(gs, n=2):
    h = gs.get('macro_history', [])
    if len(h) < n + 1:
        return False
    return all(h[-(i+1)]['price_index'] < h[-(i+2)]['price_index']
               for i in range(n) if len(h) > i + 1)


def smart_player_action(gs):
    player = gs['player']
    rate   = gs['macro']['rate']
    cash   = player['cash']
    port   = player['portfolio']
    year   = current_real_year(gs)

    if rate > _SELL_RATE_GATE and port:
        return 'sell', None, min(port, key=lambda p: p['value'])['id'], 0.0
    if _prices_falling(gs, 2) and port:
        return 'sell', None, min(port, key=lambda p: p['value'])['id'], 0.0
    if rate < 5.5 and gs.get('refinance_cooldown', 0) == 0 and len(port) >= 2:
        candidates = [(p, int(p['value'] * _REFI_LTV) -
                       next((m['loan'] for m in player['mortgages'] if m['prop_id'] == p['id']), 0))
                      for p in port]
        candidates = [(p, h) for p, h in candidates if h > 20_000]
        if candidates:
            best_p, _ = max(candidates, key=lambda x: x[1])
            return 'remortgage', best_p['id'], None, _REFI_LTV
    if rate <= _BUY_RATE_GATE:
        region_count = collections.Counter(p.get('region') for p in port)
        affordable = [p for p in gs['market']
                      if not p.get('auction')
                      and p['value'] * (1 - _BUY_LTV) + calc_sdlt(p['value'], year) <= cash]
        if affordable:
            diverse = [p for p in affordable if region_count.get(p.get('region'), 0) < 3]
            pool = diverse if diverse else affordable
            return 'buy', max(pool, key=lambda p: p['value'])['id'], None, _BUY_LTV
    return 'hold', None, None, 0.0


def snapshot(gs):
    """Return per-actor wealth snapshot plus macro for this tick."""
    player = gs['player']
    pv     = sum(p['value'] for p in player['portfolio'])
    pd     = sum(m['loan']  for m in player.get('mortgages', []))
    actors = {
        'You': {'cash': player['cash'], 'portfolio_value': pv,
                'debt': pd, 'equity': pv - pd},
    }
    for ai in gs['ai']:
        av = ai.get('portfolio_value', 0)
        ad = ai.get('total_debt', 0)
        actors[ai['name']] = {
            'cash': ai['cash'], 'portfolio_value': av,
            'debt': ad, 'equity': av - ad,
        }
    return {
        'tick': gs['tick'],
        'rate': gs['macro']['rate'],
        'price_index': gs['macro']['price_index'],
        'actors': actors,
    }


def run_one(total_ticks=80):
    gs = init_game_state(total_ticks=total_ticks)
    history = [snapshot(gs)]

    for _ in range(total_ticks):
        action, buy_id, sell_id, ltv = smart_player_action(gs)
        apply_player_action(gs, action, buy_id, sell_id, ltv=ltv)
        apply_ai_actions(gs)
        advance_tick(gs)
        history.append(snapshot(gs))
        if gs.get('end'):
            break

    lb     = gs['leaderboard']
    winner = lb[0]['name']
    start  = f"{gs['real_start_year']}Q{gs['real_start_quarter']}"
    print(f"Start: {start}  Winner: {winner}  Score: £{lb[0]['score']:,.0f}")
    for e in lb:
        print(f"  {e['name']:<20} £{e['score']:>12,.0f}")
    return history, winner, start


def plot(history, winner, start):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ticks       = [s['tick'] for s in history]
    rates       = [s['rate'] for s in history]
    price_index = [s['price_index'] for s in history]

    actor_colours = {
        'You':           '#00FF88',
        'Mr Hugh Price': '#FBBF24',
        'Mr Max Lever':  '#F87171',
    }
    actors = ['You', 'Mr Hugh Price', 'Mr Max Lever']

    fig, axes = plt.subplots(5, 1, figsize=(14, 18), sharex=True,
                             gridspec_kw={'height_ratios': [2, 2, 2, 1, 1]})
    ax_equity, ax_cash, ax_debt, ax_rate, ax_pi = axes

    for name in actors:
        col   = actor_colours[name]
        lw    = 2.5 if name == winner else 1.4
        alpha = 1.0 if name == winner else 0.55
        ls    = '-'  if name == winner else '--'
        label = f'{name}  ← WINNER' if name == winner else name

        equity = [s['actors'][name]['equity'] for s in history]
        cash   = [s['actors'][name]['cash']   for s in history]
        debt   = [s['actors'][name]['debt']   for s in history]

        ax_equity.plot(ticks, equity, color=col, lw=lw, alpha=alpha, ls=ls, label=label)
        ax_cash.plot(  ticks, cash,   color=col, lw=lw, alpha=alpha, ls=ls, label=label)
        ax_debt.plot(  ticks, debt,   color=col, lw=lw, alpha=alpha, ls=ls, label=label)

    ax_rate.plot(ticks, rates,       color='#94a3b8', lw=1.8, label='Base rate %')
    ax_pi.plot(  ticks, price_index, color='#60a5fa', lw=1.8, label='Price index')

    def fmt_gbp(ax):
        import matplotlib.ticker as mticker
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'£{x/1e6:.1f}M'))

    fmt_gbp(ax_equity)
    fmt_gbp(ax_cash)
    fmt_gbp(ax_debt)

    ax_equity.set_title(f'Property equity  (start {start}, winner: {winner})',
                        fontsize=12, fontweight='bold')
    ax_cash.set_title('Cash', fontsize=11, fontweight='bold')
    ax_debt.set_title('Mortgage debt', fontsize=11, fontweight='bold')
    ax_rate.set_title('Base interest rate (%)', fontsize=11, fontweight='bold')
    ax_pi.set_title('Normalised price index', fontsize=11, fontweight='bold')
    ax_pi.set_xlabel('Game tick (each = 3 months)', fontsize=10)

    for ax in [ax_equity, ax_cash, ax_debt]:
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(alpha=0.25)
    ax_rate.grid(alpha=0.25)
    ax_pi.grid(alpha=0.25)

    # Shade periods of falling prices
    for i in range(1, len(ticks)):
        if price_index[i] < price_index[i - 1]:
            for ax in axes:
                ax.axvspan(ticks[i-1], ticks[i], alpha=0.06, color='red', lw=0)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), 'winner_wealth.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'\nPlot saved: {out}')


if __name__ == '__main__':
    history, winner, start = run_one(total_ticks=40)
    plot(history, winner, start)
