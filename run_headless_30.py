"""Run 30 headless games using the web app engine. Player holds every turn."""

import sys
import os
import collections
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui_web'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui_kivy'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))

from app import (init_game_state, advance_tick, apply_player_action,
                  apply_ai_actions, calc_sdlt, current_real_year)

_BUY_RATE_GATE  = 9.0    # buy when rate at or below this (matches Mr Max Lever)
_SELL_RATE_GATE = 11.5   # sell when rate exceeds this
_BUY_LTV        = 0.75   # max leverage — capital growth dominates score
_REFI_LTV       = 0.70   # refi target LTV — conservative enough to stay solvent


def _prices_falling(gs, n=2):
    history = gs.get('macro_history', [])
    if len(history) < n + 1:
        return False
    return all(
        history[-(i + 1)]['price_index'] < history[-(i + 2)]['price_index']
        for i in range(n)
        if len(history) > i + 1
    )


def smart_player_action(gs):
    """
    Capital-growth strategy with leverage and refi:
    - Buy highest-value affordable property at 75% LTV when rate <= 9%
    - Prefer regions not already over-concentrated (avoid penalty)
    - Remortgage best property to extract equity when rates are low
    - Sell lowest-value holding to de-risk when rate spikes or prices fall 2+ ticks
    """
    player  = gs['player']
    market  = gs['market']
    rate    = gs['macro']['rate']
    cash    = player['cash']
    port    = player['portfolio']
    year    = current_real_year(gs)

    # Sell: rate spike or sustained price falls — shed lowest-value property
    if rate > _SELL_RATE_GATE and port:
        worst = min(port, key=lambda p: p['value'])
        return 'sell', None, worst['id'], 0.0

    if _prices_falling(gs, n=2) and port:
        worst = min(port, key=lambda p: p['value'])
        return 'sell', None, worst['id'], 0.0

    # Remortgage: extract equity to redeploy when rates are low
    if rate < 5.5 and gs.get('refinance_cooldown', 0) == 0 and len(port) >= 2:
        candidates = []
        for p in port:
            existing = next((m['loan'] for m in player['mortgages'] if m['prop_id'] == p['id']), 0)
            headroom = int(p['value'] * _REFI_LTV) - existing
            if headroom > 20_000:
                candidates.append((p, headroom))
        if candidates:
            best_p, _ = max(candidates, key=lambda x: x[1])
            return 'remortgage', best_p['id'], None, _REFI_LTV

    # Buy: highest-value property we can afford, avoiding concentration penalty
    if rate <= _BUY_RATE_GATE:
        region_count = collections.Counter(p.get('region') for p in port)
        affordable = [
            p for p in market
            if not p.get('auction')
            and p['value'] * (1 - _BUY_LTV) + calc_sdlt(p['value'], year) <= cash
        ]
        if affordable:
            # Prefer regions with < 3 properties to avoid concentration penalty
            diverse = [p for p in affordable if region_count.get(p.get('region'), 0) < 3]
            pool = diverse if diverse else affordable
            best = max(pool, key=lambda p: p['value'])
            return 'buy', best['id'], None, _BUY_LTV

    return 'hold', None, None, 0.0


def run_game(game_num, total_ticks=80):
    gs = init_game_state(total_ticks=total_ticks)
    start_year = gs['real_start_year']
    start_quarter = gs['real_start_quarter']

    for _ in range(total_ticks):
        action, buy_id, sell_id, ltv = smart_player_action(gs)
        apply_player_action(gs, action, buy_id, sell_id, ltv=ltv)
        apply_ai_actions(gs)
        ended = advance_tick(gs)
        if ended or gs.get('end'):
            break

    lb = gs['leaderboard']
    winner = lb[0]['name'] if lb else 'Unknown'
    second = lb[1]['name'] if len(lb) > 1 else 'Unknown'
    winner_score = lb[0]['score'] if lb else 0
    second_score = lb[1]['score'] if len(lb) > 1 else 0
    you_entry = next((e for e in lb if e['name'] == 'You'), None)
    you_rank  = lb.index(you_entry) + 1 if you_entry else '-'
    you_score = you_entry['score'] if you_entry else 0

    print(f"  Game {game_num:>3}  {start_year}Q{start_quarter}  "
          f"1st: {winner:<20} £{winner_score:>10,.0f}  "
          f"2nd: {second:<20} £{second_score:>10,.0f}  "
          f"You: rank={you_rank} £{you_score:>10,.0f}", flush=True)

    return {
        'game': game_num,
        'start_year': start_year,
        'start_quarter': start_quarter,
        'winner': winner,
        'second': second,
        'winner_score': winner_score,
        'second_score': second_score,
        'you_rank': you_rank,
        'you_score': you_score,
    }


def main():
    n_games = 30
    total_ticks = 80
    print(f"Running {n_games} headless games ({total_ticks} ticks each)...\n")

    records = []
    for g in range(1, n_games + 1):
        rec = run_game(g, total_ticks)
        records.append(rec)

    # Summary table
    wins = collections.Counter(r['winner'] for r in records)
    seconds = collections.Counter(r['second'] for r in records)
    you_ranks = collections.Counter(r['you_rank'] for r in records)
    names = sorted(set(wins) | set(seconds) | {'You'}, key=lambda n: -wins.get(n, 0))

    print(f"\n{'-'*60}")
    print(f"  {'Name':<22} {'1st':>5}  {'2nd':>5}  {'top2':>5}")
    print(f"  {'-'*50}")
    for name in names:
        w = wins.get(name, 0)
        s = seconds.get(name, 0)
        print(f"  {name:<22} {w:>5}  {s:>5}  {w+s:>5}")

    print(f"\n  Your rank distribution across {n_games} games:")
    for rank in [1, 2, 3]:
        cnt = you_ranks.get(rank, 0)
        print(f"    Rank {rank}: {cnt:>3}  ({cnt/n_games*100:.0f}%)")

    # Plot
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    actors = ['You', 'Mr Hugh Price', 'Mr Max Lever']
    colours = {'You': '#00FF88', 'Mr Hugh Price': '#FBBF24', 'Mr Max Lever': '#F87171'}
    rng = np.random.default_rng(42)

    fig, (ax_win, ax_second) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    actor_to_y = {a: i for i, a in enumerate(actors)}
    xlim = (min(r['start_year'] for r in records) - 0.5,
            max(r['start_year'] for r in records) + 0.5)

    def draw_panel(ax, records, key, title, wins_counter):
        for rec in records:
            name = rec[key]
            y = actor_to_y.get(name, len(actors))
            jit = rng.uniform(-0.2, 0.2)
            ax.scatter(rec['start_year'] + rng.uniform(-0.1, 0.1),
                       y + jit,
                       color=colours.get(name, '#888'), alpha=0.7, s=60, zorder=3)
        ax.set_yticks(range(len(actors)))
        ax.set_yticklabels(actors, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        ax.set_xlim(xlim)
        n = len(records)
        for name, y in actor_to_y.items():
            w = wins_counter.get(name, 0)
            ax.text(xlim[1] + 0.1, y,
                    f"{w}/{n}  ({w/n*100:.0f}%)",
                    va='center', fontsize=9, color=colours.get(name, '#888'))

    draw_panel(ax_win,    records, 'winner', f'Winner by start year  (n={n_games})',    wins)
    draw_panel(ax_second, records, 'second', f'2nd place by start year  (n={n_games})', seconds)

    ax_second.set_xlabel('Game start year', fontsize=11)

    patches = [plt.matplotlib.patches.Patch(color=colours[a], label=a) for a in actors]
    fig.legend(handles=patches, loc='lower center', ncol=3, fontsize=10,
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(os.path.dirname(__file__), 'wins_by_year_30.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {out}")


if __name__ == '__main__':
    main()
