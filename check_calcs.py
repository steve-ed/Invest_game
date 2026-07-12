"""
Run 30 headless games, log full results, and verify all score calculations.

Per-game log includes:
  - Start year, ticks played
  - Final portfolio/cash/rent/debt for each actor
  - Score component breakdown
  - Leaderboard vs manually recalculated scores (flags mismatches)

Calculation checks:
  - Player: score = portfolio + cash + rent*0.4 - leverage_penalty - concentration_penalty
  - AI: score = portfolio + cash + cumulative_rent*0.4 (no penalties applied to AIs)
  - Leverage penalty: excess debt above 50% LTV * 10%
  - Concentration penalty: 4+ props in one region -> 5% avg_value * excess count
"""

import sys, random, collections, textwrap
sys.path.insert(0, 'ui_web')

from app import (
    init_game_state, advance_tick, apply_player_action,
    leverage_penalty, concentration_penalty, score_for_archetype,
)

ACTORS = ['You', 'Mr Hugh Price', 'Mr Max Lever']
COLOURS = {'You': '#00FF88', 'Mr Hugh Price': '#FBBF24', 'Mr Max Lever': '#F87171'}


def run_game(game_num, seed):
    random.seed(seed)
    gs = init_game_state(20, 'balanced')
    start_year = gs['real_start_year']

    for _ in range(gs['total_ticks']):
        market = gs['market']
        player = gs['player']
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
                            ltv=0.75 if action == 'buy' else 0.0, rate_type='variable')
        if advance_tick(gs):
            break

    # --- Player score components ---
    player = gs['player']
    p_portfolio = sum(p['value'] for p in player['portfolio'])
    p_cash      = player['cash']
    p_rent      = player.get('cumulative_rent', 0)
    p_debt      = sum(m['loan'] for m in player.get('mortgages', []))
    p_lev_pen   = leverage_penalty(p_portfolio, p_debt)
    p_con_pen   = concentration_penalty(player['portfolio'])
    p_score_calc = p_portfolio + p_cash + int(p_rent * 0.4) - p_lev_pen - p_con_pen

    # --- AI score components ---
    ai_data = {}
    for ai in gs['ai']:
        ai_portfolio = ai['portfolio_value']
        ai_cash      = ai['cash']
        ai_rent      = ai.get('cumulative_rent', 0)
        ai_debt      = ai.get('total_debt', 0)
        ai_score_calc = ai_portfolio + ai_cash + int(ai_rent * 0.4)
        ai_data[ai['name']] = {
            'portfolio': ai_portfolio, 'cash': ai_cash,
            'rent': ai_rent, 'debt': ai_debt, 'score_calc': ai_score_calc,
        }

    # --- Leaderboard scores ---
    lb = {e['name']: e['score'] for e in gs['leaderboard']}

    # --- Mismatch check ---
    mismatches = []
    if abs(lb.get('You', 0) - p_score_calc) > 1:
        mismatches.append(f"  MISMATCH You: leaderboard={lb.get('You',0):,.0f}  calc={p_score_calc:,.0f}")
    for name, d in ai_data.items():
        if abs(lb.get(name, 0) - d['score_calc']) > 1:
            mismatches.append(
                f"  MISMATCH {name}: leaderboard={lb.get(name,0):,.0f}  calc={d['score_calc']:,.0f}"
            )

    ranked = sorted(gs['leaderboard'], key=lambda e: e['score'], reverse=True)

    return {
        'game':       game_num,
        'start_year': start_year,
        'ticks':      gs['tick'],
        'first':      ranked[0]['name'],
        'second':     ranked[1]['name'],
        'third':      ranked[2]['name'],
        'player': {
            'portfolio': p_portfolio, 'cash': p_cash, 'rent': p_rent,
            'debt': p_debt, 'lev_pen': p_lev_pen, 'con_pen': p_con_pen,
            'score_calc': p_score_calc, 'score_lb': lb.get('You', 0),
            'props': len(player['portfolio']),
        },
        'ai': ai_data,
        'lb': lb,
        'mismatches': mismatches,
    }


def fmt(n): return f'£{n:>12,.0f}'


def main():
    games = 30
    print(f"Running {games} games and checking calculations...\n")

    records = []
    all_mismatches = []

    for g in range(1, games + 1):
        rec = run_game(g, seed=1000 + g)
        records.append(rec)

        p  = rec['player']
        lb = rec['lb']

        print(f"Game {g:>3}  {rec['start_year']}  "
              f"1st={rec['first']:<16} 2nd={rec['second']:<16} 3rd={rec['third']}")

        # Player breakdown
        print(f"         YOU:           portfolio={fmt(p['portfolio'])}  "
              f"cash={fmt(p['cash'])}  rent={fmt(p['rent'])}  debt={fmt(p['debt'])}")
        print(f"                        lev_pen={fmt(p['lev_pen'])}  "
              f"con_pen={fmt(p['con_pen'])}  "
              f"score={fmt(p['score_calc'])}  props={p['props']}")

        # AI breakdowns
        for name, d in rec['ai'].items():
            print(f"         {name:<16} portfolio={fmt(d['portfolio'])}  "
                  f"cash={fmt(d['cash'])}  rent={fmt(d['rent'])}  debt={fmt(d['debt'])}")
            print(f"                        score={fmt(d['score_calc'])}")

        if rec['mismatches']:
            for m in rec['mismatches']:
                print(f"  *** {m}")
            all_mismatches.extend(rec['mismatches'])
        print()

    # --- Summary table ---
    wins   = collections.Counter(r['first']  for r in records)
    second = collections.Counter(r['second'] for r in records)
    third  = collections.Counter(r['third']  for r in records)

    print(f"\n{'-'*60}")
    print(f"  {'Actor':<18} {'1st':>5}  {'2nd':>5}  {'3rd':>5}  {'1st%':>6}")
    print(f"  {'-'*55}")
    for a in ACTORS:
        w = wins.get(a, 0)
        print(f"  {a:<18} {w:>5}  {second.get(a,0):>5}  {third.get(a,0):>5}  {w/games*100:>5.1f}%")
    print(f"{'-'*60}")

    # --- Calculation audit summary ---
    print(f"\n{'='*60}")
    print(f"  CALCULATION AUDIT")
    print(f"{'='*60}")
    if all_mismatches:
        print(f"  {len(all_mismatches)} MISMATCHES FOUND:")
        for m in all_mismatches:
            print(m)
    else:
        print(f"  All {games} games: leaderboard scores match manual calculations. OK")

    # --- Range checks ---
    player_scores = [r['player']['score_calc'] for r in records]
    print(f"\n  Player score range:  {fmt(min(player_scores))} – {fmt(max(player_scores))}")
    print(f"  Avg player score:    {fmt(sum(player_scores)/len(player_scores))}")

    lev_pens = [r['player']['lev_pen'] for r in records]
    con_pens = [r['player']['con_pen'] for r in records]
    print(f"  Games with leverage penalty:      {sum(1 for x in lev_pens if x > 0)}")
    print(f"  Games with concentration penalty: {sum(1 for x in con_pens if x > 0)}")
    print(f"  Max leverage penalty seen:        {fmt(max(lev_pens))}")
    print(f"  Max concentration penalty seen:   {fmt(max(con_pens))}")

    # --- Plot ---
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(14, 5))
    actor_y = {a: i for i, a in enumerate(ACTORS)}
    years = [r['start_year'] for r in records]

    for rec in records:
        s  = rec['first']
        y  = actor_y.get(s, len(ACTORS))
        jy = rng.uniform(-0.2, 0.2)
        ax.scatter(rec['start_year'], y + jy,
                   color=COLOURS.get(s, '#888'), s=80, alpha=0.85, zorder=3,
                   edgecolors='white', linewidths=0.5)

    ax.set_yticks(range(len(ACTORS)))
    ax.set_yticklabels(ACTORS, fontsize=11)
    ax.set_xlabel('Game start year', fontsize=11)
    ax.set_title(f'Winner by game start year — {games} games (20 turns each)', fontsize=13)
    ax.grid(axis='x', alpha=0.3)
    xlim = (min(years) - 1, max(years) + 3)
    ax.set_xlim(xlim)
    for a, y in actor_y.items():
        w = wins.get(a, 0)
        ax.text(xlim[1] + 0.2, y, f"{w} wins ({w/games*100:.0f}%)",
                va='center', fontsize=9, color=COLOURS.get(a, '#888'))
    patches = [mpatches.Patch(color=COLOURS[a], label=a) for a in ACTORS]
    ax.legend(handles=patches, loc='upper left', fontsize=9)
    plt.tight_layout()
    out = 'wins_by_year_30.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {out}")


if __name__ == '__main__':
    main()
