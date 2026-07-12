"""
Run 30 headless games using the web app engine.
Player strategy: buy-and-hold (buy cheapest affordable property each turn).
Logs 1st, 2nd, 3rd for each game and plots winner vs start year.
"""

import sys, random, collections
sys.path.insert(0, 'ui_web')

from app import (
    init_game_state, advance_tick, apply_player_action,
    leverage_penalty, concentration_penalty, score_for_archetype,
)

COLOURS = {
    'You':           '#00FF88',
    'Mr Hugh Price': '#FBBF24',
    'Mr Max Lever':  '#F87171',
}


def run_game(game_num, seed):
    random.seed(seed)
    gs = init_game_state(20, 'balanced')
    start_year = gs['real_start_year']

    for _ in range(gs['total_ticks']):
        market = gs['market']
        player = gs['player']

        # Strategy: buy best-yielding affordable property (25% deposit), no cap
        action, buy_id = 'hold', None
        from collections import Counter
        region_counts = Counter(p['region'] for p in player['portfolio'])
        affordable = [
            p for p in market
            if not p.get('auction')
            and player['cash'] >= p['value'] * 0.25
            and region_counts.get(p['region'], 0) < 3
        ]
        if affordable:
            prop = max(affordable, key=lambda p: p['rent'] / p['value'])
            action, buy_id = 'buy', prop['id']

        apply_player_action(gs, action, buy_id, None,
                            ltv=0.75 if action == 'buy' else 0.0,
                            rate_type='variable')
        game_over = advance_tick(gs)
        if game_over:
            break

    lb = sorted(gs['leaderboard'], key=lambda e: e['score'], reverse=True)
    places = [(e['name'], e['score']) for e in lb]

    print(f"  Game {game_num:>3}  {start_year}  "
          f"1st={places[0][0]:<14} £{places[0][1]:>10,.0f}  "
          f"2nd={places[1][0]:<14} £{places[1][1]:>10,.0f}  "
          f"3rd={places[2][0]:<14} £{places[2][1]:>10,.0f}",
          flush=True)

    return {
        'game':       game_num,
        'start_year': start_year,
        'first':      places[0][0],
        'second':     places[1][0],
        'third':      places[2][0],
        'scores':     {e['name']: e['score'] for e in lb},
    }


def main():
    games = 30
    print(f"Running {games} headless games (20 turns each)...\n")
    records = []
    for g in range(1, games + 1):
        rec = run_game(g, seed=1000 + g)
        records.append(rec)

    # Summary table
    wins   = collections.Counter(r['first']  for r in records)
    second = collections.Counter(r['second'] for r in records)
    third  = collections.Counter(r['third']  for r in records)
    actors = ['You', 'Mr Hugh Price', 'Mr Max Lever']

    print(f"\n{'-'*55}")
    print(f"  {'Actor':<16} {'1st':>5}  {'2nd':>5}  {'3rd':>5}  {'1st%':>6}")
    print(f"  {'-'*50}")
    for a in actors:
        w = wins.get(a, 0)
        print(f"  {a:<16} {w:>5}  {second.get(a,0):>5}  {third.get(a,0):>5}  {w/games*100:>5.1f}%")
    print(f"{'-'*55}")

    # Plot
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(14, 5))

    actor_y = {a: i for i, a in enumerate(actors)}
    years = [r['start_year'] for r in records]

    for rec in records:
        for place, actor in [(rec['first'], rec['first']),
                             (rec['second'], rec['second']),
                             (rec['third'], rec['third'])]:
            break  # only plot winner

        s  = rec['first']
        y  = actor_y[s]
        jy = rng.uniform(-0.2, 0.2)
        ax.scatter(rec['start_year'], y + jy,
                   color=COLOURS[s], s=80, alpha=0.85, zorder=3,
                   edgecolors='white', linewidths=0.5)

    ax.set_yticks(range(len(actors)))
    ax.set_yticklabels(actors, fontsize=11)
    ax.set_xlabel('Game start year', fontsize=11)
    ax.set_title(f'Winner by game start year — {games} games (20 turns each)', fontsize=13)
    ax.grid(axis='x', alpha=0.3)

    xlim = (min(years) - 1, max(years) + 3)
    ax.set_xlim(xlim)

    # Win count annotations on right
    for a, y in actor_y.items():
        w = wins.get(a, 0)
        ax.text(xlim[1] + 0.2, y, f"{w} wins ({w/games*100:.0f}%)",
                va='center', fontsize=9, color=COLOURS[a])

    patches = [mpatches.Patch(color=COLOURS[a], label=a) for a in actors]
    ax.legend(handles=patches, loc='upper left', fontsize=9)

    plt.tight_layout()
    out = 'wins_by_year_30.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {out}")


if __name__ == '__main__':
    main()
