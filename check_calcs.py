"""
Run 30 headless games and verify all score calculations against the live engine.

Score formula (ui_web/app.py  score_for_archetype):
    score = portfolio_value - total_debt + cash - concentration_penalty

Per-game log:
  - Start year, ticks played
  - Final portfolio / cash / debt for each actor
  - Concentration penalty
  - Computed score vs leaderboard score (flags any mismatch)
"""

import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui_web'))

from app import (
    init_game_state, advance_tick, apply_player_action, apply_ai_actions,
    calc_sdlt, current_real_year, concentration_penalty, score_for_archetype,
)

ACTORS   = ['You', 'Mr Hugh Price', 'Mr Max Lever']
COLOURS  = {'You': '#00FF88', 'Mr Hugh Price': '#FBBF24', 'Mr Max Lever': '#F87171'}

_BUY_LTV        = 0.75
_BUY_RATE_GATE  = 9.0
_SELL_RATE_GATE = 11.5


def _smart_action(gs):
    player = gs['player']
    market = gs['market']
    rate   = gs['macro']['rate']
    cash   = player['cash']
    port   = player['portfolio']
    year   = current_real_year(gs)

    if rate > _SELL_RATE_GATE and port:
        worst = min(port, key=lambda p: p['value'])
        return 'sell', None, worst['id'], 0.0

    if rate <= _BUY_RATE_GATE:
        region_count = collections.Counter(p.get('region') for p in port)
        affordable = [
            p for p in market
            if not p.get('auction')
            and p['value'] * (1 - _BUY_LTV) + calc_sdlt(p['value'], year) <= cash
        ]
        if affordable:
            diverse = [p for p in affordable if region_count.get(p.get('region'), 0) < 3]
            pool = diverse if diverse else affordable
            best = max(pool, key=lambda p: p['value'])
            return 'buy', best['id'], None, _BUY_LTV

    return 'hold', None, None, 0.0


def _actor_score(portfolio, mortgages, cash):
    pv       = sum(p['value'] for p in portfolio)
    debt     = sum(m['loan'] for m in mortgages)
    con_pen  = concentration_penalty(portfolio)
    computed = score_for_archetype('balanced', pv, cash, 0, debt, concentration_pen=con_pen)
    return pv, debt, con_pen, computed


def run_game(game_num, total_ticks=20):
    gs = init_game_state(total_ticks=total_ticks)
    start_year = gs['real_start_year']

    for _ in range(total_ticks):
        action, buy_id, sell_id, ltv = _smart_action(gs)
        apply_player_action(gs, action, buy_id, sell_id, ltv=ltv)
        apply_ai_actions(gs)
        if advance_tick(gs) or gs.get('end'):
            break

    lb = {e['name']: e['score'] for e in gs['leaderboard']}

    # ── Player ───────────────────────────────────────────────────────────────
    p = gs['player']
    p_pv, p_debt, p_con, p_calc = _actor_score(
        p['portfolio'], p.get('mortgages', []), p['cash'])
    p_lb   = lb.get('You', 0)
    p_miss = abs(p_lb - p_calc) > 1

    # ── AIs ──────────────────────────────────────────────────────────────────
    ai_rows = []
    for ai in gs['ai']:
        ai_port  = ai.get('portfolio', [])
        ai_mtg   = ai.get('mortgages', [])
        a_pv, a_debt, a_con, a_calc = _actor_score(ai_port, ai_mtg, ai['cash'])
        a_lb   = lb.get(ai['name'], 0)
        a_miss = abs(a_lb - a_calc) > 1
        ai_rows.append({
            'name': ai['name'], 'cash': ai['cash'], 'pv': a_pv, 'debt': a_debt,
            'con': a_con, 'calc': a_calc, 'lb': a_lb, 'miss': a_miss,
        })

    ranked = sorted(gs['leaderboard'], key=lambda e: e['score'], reverse=True)
    mismatches = (
        [f"  MISMATCH You: lb={p_lb:,.0f}  calc={p_calc:,.0f}"] if p_miss else []
    ) + [
        f"  MISMATCH {r['name']}: lb={r['lb']:,.0f}  calc={r['calc']:,.0f}"
        for r in ai_rows if r['miss']
    ]

    return {
        'game': game_num, 'start_year': start_year, 'ticks': gs['tick'],
        'first':  ranked[0]['name'] if ranked else '?',
        'second': ranked[1]['name'] if len(ranked) > 1 else '?',
        'third':  ranked[2]['name'] if len(ranked) > 2 else '?',
        'player': {'pv': p_pv, 'cash': p['cash'], 'debt': p_debt,
                   'con': p_con, 'calc': p_calc, 'lb': p_lb, 'miss': p_miss,
                   'props': len(p['portfolio'])},
        'ai': ai_rows, 'lb': lb, 'mismatches': mismatches,
    }


def fmt(n): return f'£{n:>12,.0f}'


def main():
    games = 30
    print(f"Running {games} games and verifying score calculations...\n")

    records, all_mismatches = [], []

    for g in range(1, games + 1):
        rec = run_game(g)
        records.append(rec)
        p = rec['player']

        print(f"Game {g:>3}  {rec['start_year']}  "
              f"1st={rec['first']:<20} 2nd={rec['second']:<20} 3rd={rec['third']}")
        print(f"  You:  pv={fmt(p['pv'])}  cash={fmt(p['cash'])}  "
              f"debt={fmt(p['debt'])}  con_pen={fmt(p['con'])}  "
              f"score={fmt(p['calc'])}  lb={fmt(p['lb'])}  "
              f"{'OK' if not p['miss'] else '*** MISMATCH ***'}  props={p['props']}")
        for r in rec['ai']:
            print(f"  {r['name']:<20} pv={fmt(r['pv'])}  cash={fmt(r['cash'])}  "
                  f"debt={fmt(r['debt'])}  con_pen={fmt(r['con'])}  "
                  f"score={fmt(r['calc'])}  lb={fmt(r['lb'])}  "
                  f"{'OK' if not r['miss'] else '*** MISMATCH ***'}")
        if rec['mismatches']:
            for m in rec['mismatches']:
                print(m)
            all_mismatches.extend(rec['mismatches'])
        print()

    # ── Summary table ────────────────────────────────────────────────────────
    wins   = collections.Counter(r['first']  for r in records)
    second = collections.Counter(r['second'] for r in records)
    third  = collections.Counter(r['third']  for r in records)

    print(f"\n{'-'*60}")
    print(f"  {'Actor':<22} {'1st':>5}  {'2nd':>5}  {'3rd':>5}  {'1st%':>6}")
    print(f"  {'-'*55}")
    for a in ACTORS:
        w = wins.get(a, 0)
        print(f"  {a:<22} {w:>5}  {second.get(a,0):>5}  {third.get(a,0):>5}  {w/games*100:>5.1f}%")
    print(f"{'-'*60}")

    # ── Calculation audit ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  CALCULATION AUDIT  (score = pv - debt + cash - con_pen)")
    print(f"{'='*60}")
    if all_mismatches:
        print(f"  {len(all_mismatches)} MISMATCHES FOUND:")
        for m in all_mismatches:
            print(m)
    else:
        print(f"  All {games} games: leaderboard scores match manual calculations. OK")

    player_scores = [r['player']['calc'] for r in records]
    con_pens      = [r['player']['con']  for r in records]
    print(f"\n  Player score range: {fmt(min(player_scores))} – {fmt(max(player_scores))}")
    print(f"  Avg player score:   {fmt(sum(player_scores)/len(player_scores))}")
    print(f"  Games with concentration penalty: {sum(1 for x in con_pens if x > 0)}")
    print(f"  Max concentration penalty:        {fmt(max(con_pens))}")


if __name__ == '__main__':
    main()
