import sys
import os
import copy
import random
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_kivy'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
import dummy_data as dd
import uk_macro_history as hist
import uk_regional_hpi as regional_hpi

from flask import Flask, render_template, redirect, url_for, request, session

app = Flask(__name__)
app.secret_key = 'realestgame-dev-key'

# Module-level game state (single-user prototype)
GAME_STATE = {}

# ---------------------------------------------------------------------------
# Scenario arc
# ---------------------------------------------------------------------------

SCENARIO_ARC_40 = [
    # (start_tick, end_tick_exclusive, phase_name, description, quarterly_price_growth, rent_growth_delta, rate_delta)
    (0,  12, "Baseline",    "Steady conditions. Good time to build positions.",      0.020,  0.0,   0.0),
    (12, 22, "Boom",        "Prices rising fast. Yield compression underway.",       0.045,  1.5,   0.5),
    (22, 30, "Correction",  "Market overheated. Prices falling, rates elevated.",   -0.020, -1.0,   1.0),
    (30, 40, "Recovery",    "Rates easing, rents recovering. Selective buyers win.", 0.015,  0.5,  -1.0),
]

SCENARIO_ARC_80 = [
    (0,  16, "Baseline",    "Steady conditions. Good time to build positions.",           0.020,  0.0,   0.0),
    (16, 32, "Boom",        "Prices rising fast. Yield compression underway.",            0.040,  1.5,   0.5),
    (32, 44, "Correction",  "Market overheated. Prices falling, rates elevated.",        -0.020, -1.0,   1.0),
    (44, 56, "Recovery",    "Rates easing, rents recovering. Selective buyers win.",      0.015,  0.5,  -0.5),
    (56, 66, "Expansion",   "Second cycle underway. Optimism returns to the market.",     0.030,  0.5,  -0.5),
    (66, 74, "Peak",        "Prices at historic highs. Yields thin. Caution advised.",    0.010,  0.0,   0.5),
    (74, 80, "Crash",       "Sharp correction. Leveraged players face forced sales.",    -0.045, -2.0,   1.5),
]

SCENARIO_ARCS = {40: SCENARIO_ARC_40, 80: SCENARIO_ARC_80}


def get_scenario_phase(tick, arc):
    """Return the arc entry covering the given tick."""
    for phase in arc:
        start, end, name, desc, growth, rent_delta, rate_delta = phase
        if start <= tick < end:
            return phase
    return arc[-1]  # fallback to last phase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def gross_yield(prop):
    return prop['rent'] * 12 / prop['value'] * 100


def _void_chance(prop):
    y = prop['rent'] * 12 / prop['value'] * 100
    return max(0.0, (y - 3.0) / 100.0)


def _apply_void_risk(gs):
    for p in gs['player']['portfolio']:
        went_vacant = random.random() < _void_chance(p)
        p['vacant'] = went_vacant
        if went_vacant:
            gs['news'].append(f"{p['id']} went vacant this quarter — no rent collected.")


def player_monthly_mortgage(gs):
    """Total monthly mortgage payment across all player mortgages."""
    return sum(m['monthly_payment'] for m in gs['player'].get('mortgages', []))


def player_net_worth(gs):
    """Portfolio value + cash - total outstanding loans."""
    portfolio_val = sum(p['value'] for p in gs['player']['portfolio'])
    total_debt = sum(m['loan'] for m in gs['player'].get('mortgages', []))
    return portfolio_val + gs['player']['cash'] - total_debt


AGENT_FEE_RATE = 0.015          # 1.5% of sale price charged by selling agent
FIX_PREMIUMS   = {'variable': 2.0, 'fixed_2yr': 2.5, 'fixed_5yr': 2.25}
FIX_DURATIONS  = {'fixed_2yr': 8, 'fixed_5yr': 20}   # ticks (quarterly periods)

EPC_UPGRADE_COST    = 5000
EPC_RENT_PENALTY    = 0.15   # fraction of rent lost for non-compliant properties
LICENSING_COST_PROP = 1500
RENT_FREEZE_TURNS   = 4


def calc_sdlt(value, year):
    """Stamp Duty Land Tax for an investment property purchase."""
    if year >= 2016:
        # 3% surcharge on all bands (April 2016 onwards)
        if value <= 125000:
            return int(value * 0.03)
        if value <= 250000:
            return int(125000 * 0.03 + (value - 125000) * 0.05)
        if value <= 925000:
            return int(125000 * 0.03 + 125000 * 0.05 + (value - 250000) * 0.08)
        return int(125000 * 0.03 + 125000 * 0.05 + 675000 * 0.08 + (value - 925000) * 0.13)
    else:
        # Pre-2016 standard SDLT (no investment surcharge)
        if value <= 125000:
            return 0
        if value <= 250000:
            return int((value - 125000) * 0.02)
        if value <= 500000:
            return int(125000 * 0.02 + (value - 250000) * 0.05)
        return int(125000 * 0.02 + 250000 * 0.05 + (value - 500000) * 0.07)


def current_real_year(gs):
    tick = gs['tick']
    if tick < len(gs['macro_slice']):
        return gs['macro_slice'][tick][0]
    return gs['macro_slice'][-1][0]


ARCHETYPE_META = {
    'income': {
        'label':  'Income Investor',
        'short':  'INCOME',
        'desc':   'Score: rent collected + cash. Portfolio value not counted.',
        'hint':   'Buy high-yield North / Wales / Scotland. Avoid heavy leverage — mortgage costs eat income.',
        'metric': 'Rent collected',
        'color':  '#FBBF24',
    },
    'growth': {
        'label':  'Capital Growth',
        'short':  'GROWTH',
        'desc':   'Score: portfolio value + cash. Maximise asset appreciation.',
        'hint':   'Target London and South. Use leverage to scale faster. Sell at peaks and reinvest.',
        'metric': 'Portfolio value',
        'color':  '#00FF88',
    },
    'balanced': {
        'label':  'Balanced',
        'short':  'BALANCED',
        'desc':   'Score: portfolio + cash + 40% of rent collected.',
        'hint':   'Diversify across regions. Manage leverage carefully for a blend of income and growth.',
        'metric': 'Portfolio + rent',
        'color':  '#F87171',
    },
}

# Approximate annual yield rates used for AI cumulative-rent estimation
# Mr Hugh Price targets high-value/lower-yield capital growth properties
# Mr Max Lever uses high leverage — income yield net of costs is modest


def leverage_penalty(portfolio_value, total_debt):
    """Penalty for leverage above 50% LTV: 10% of excess debt."""
    if portfolio_value <= 0 or total_debt <= 0:
        return 0
    safe_debt = portfolio_value * 0.5
    excess = max(0, total_debt - safe_debt)
    return int(excess * 0.10)


def concentration_penalty(portfolio):
    """Penalty for >3 properties in a single region: 5% of avg-value per excess property."""
    region_values = {}
    for p in portfolio:
        r = p.get('region', 'West')
        region_values.setdefault(r, []).append(p['value'])
    penalty = 0
    for values in region_values.values():
        count = len(values)
        if count >= 4:
            excess = count - 3
            avg_val = sum(values) / count
            penalty += int(excess * avg_val * 0.05)
    return penalty


def score_for_archetype(archetype, portfolio_value, cash, cumulative_rent, total_debt,
                        concentration_pen=0):
    return portfolio_value - total_debt + cash - concentration_pen


def player_score(gs):
    player = gs['player']
    portfolio_val = sum(p['value'] for p in player['portfolio'])
    total_debt = sum(m['loan'] for m in player.get('mortgages', []))
    cumulative_rent = player.get('cumulative_rent', 0)
    con_pen = concentration_penalty(player['portfolio'])
    return score_for_archetype(gs.get('archetype', 'balanced'), portfolio_val,
                               player['cash'], cumulative_rent, total_debt,
                               concentration_pen=con_pen)


def update_leaderboard(gs):
    archetype = gs.get('archetype', 'balanced')
    entries = [{'name': 'You', 'score': player_score(gs)}]
    for ai in gs['ai']:
        con_pen = concentration_penalty(ai.get('portfolio', []))
        score = score_for_archetype(
            archetype, ai['portfolio_value'], ai['cash'],
            ai.get('cumulative_rent', 0), ai.get('total_debt', 0),
            concentration_pen=con_pen,
        )
        entries.append({'name': ai['name'], 'score': score})
    entries.sort(key=lambda x: x['score'], reverse=True)
    gs['leaderboard'] = entries


def trend_symbol(current, previous):
    if current > previous:
        return '^'
    elif current < previous:
        return 'v'
    return '-'


# Regional profiles: price_level relative to national baseline (£165k),
# annual gross yield target, and growth_factor (amplifies national growth rate).
# London/South amplify gains AND losses; North/Wales dampen both.
REGION_PROFILES = {
    'London':   {'price_level': 2.50, 'annual_yield': 0.035, 'growth_factor': 1.40},
    'South':    {'price_level': 1.50, 'annual_yield': 0.040, 'growth_factor': 1.20},
    'East':     {'price_level': 1.20, 'annual_yield': 0.045, 'growth_factor': 1.10},
    'West':     {'price_level': 1.00, 'annual_yield': 0.048, 'growth_factor': 1.00},
    'Midlands': {'price_level': 0.85, 'annual_yield': 0.055, 'growth_factor': 0.90},
    'North':    {'price_level': 0.75, 'annual_yield': 0.060, 'growth_factor': 0.80},
    'Scotland': {'price_level': 0.80, 'annual_yield': 0.055, 'growth_factor': 0.85},
    'Wales':    {'price_level': 0.70, 'annual_yield': 0.065, 'growth_factor': 0.75},
}

_NATIONAL_BASE_VALUE = 165000
_REGIONS = list(REGION_PROFILES.keys())


def replenish_market(gs, count=2):
    """Add `count` new properties scaled to current price index and regional profile."""
    price_factor = gs['macro']['price_index'] / 100.0
    for _ in range(count):
        pid = gs['next_prop_id']
        gs['next_prop_id'] += 1
        region = _REGIONS[pid % len(_REGIONS)]
        profile = REGION_PROFILES[region]
        value = int(_NATIONAL_BASE_VALUE * profile['price_level'] * price_factor)
        rent = int(value * profile['annual_yield'] / 12)
        epc_fired = 'epc' in gs.get('reg_events_fired', [])
        gs['market'].append({
            'id': f'P-{pid}',
            'region': region,
            'value': value,
            'rent': rent,
            'epc_compliant': not epc_fired,  # new properties are non-compliant post-EPC event
        })


def _add_auction_property(gs):
    """Add one auction property at 85% of regional market value. Lasts one turn."""
    price_factor = gs['macro']['price_index'] / 100.0
    pid = gs['next_prop_id']
    gs['next_prop_id'] += 1
    region = _REGIONS[pid % len(_REGIONS)]
    profile = REGION_PROFILES[region]
    market_value = int(_NATIONAL_BASE_VALUE * profile['price_level'] * price_factor)
    value = int(market_value * 0.85)
    rent = int(value * profile['annual_yield'] / 12)
    epc_fired = 'epc' in gs.get('reg_events_fired', [])
    gs['market'].append({
        'id': f'P-{pid}',
        'region': region,
        'value': value,
        'rent': rent,
        'epc_compliant': not epc_fired,
        'auction': True,
    })
    gs['news'].append(
        f"! Auction: P-{pid} in {region} — 15% below market (£{value:,}). Bid this turn only."
    )


def _resolve_auction(gs, auction_prop, player_bid, ltv, rate_type):
    """Resolve auction bidding. Mr Max Lever bids 5% above asking; player must beat that."""
    asking = auction_prop['value']
    lever_bid = int(asking * 1.05)

    if player_bid > 0 and player_bid >= lever_bid:
        winner = 'player'
    else:
        winner = 'Mr Max Lever'

    if winner == 'player':
        player = gs['player']
        year = current_real_year(gs)
        sdlt = calc_sdlt(player_bid, year)
        loan = int(player_bid * ltv)
        deposit = player_bid - loan
        if player['cash'] >= deposit + sdlt:
            player['cash'] -= deposit + sdlt
            if loan > 0:
                premium = FIX_PREMIUMS.get(rate_type, 0.0)
                effective_rate = round(gs['macro']['rate'] + premium, 2)
                monthly_payment = round((loan * effective_rate / 100) / 12, 2)
                fix_expires = gs['tick'] + FIX_DURATIONS[rate_type] if rate_type in FIX_DURATIONS else None
                player['mortgages'].append({
                    'prop_id': auction_prop['id'],
                    'loan': loan,
                    'rate_type': rate_type,
                    'rate': effective_rate,
                    'fixed_rate': effective_rate if rate_type != 'variable' else None,
                    'fix_expires_tick': fix_expires,
                    'monthly_payment': monthly_payment,
                })
            auction_prop['value'] = player_bid
            player['portfolio'].append(auction_prop)
            gs['market'].remove(auction_prop)
            gs['news'].append(f"! Auction won: {auction_prop['id']} for £{player_bid:,}.")
        else:
            winner = 'Mr Max Lever'

    if winner != 'player':
        ai = next((a for a in gs['ai'] if a['name'] == winner), None)
        if ai:
            ai['portfolio_value'] += auction_prop['value']
            ai['props'] += 1
            if auction_prop in gs['market']:
                gs['market'].remove(auction_prop)
            gs['news'].append(
                f"! Auction: {winner} won {auction_prop['id']} with bid £{lever_bid:,}."
            )

    return winner


def get_player_rank(gs):
    for i, entry in enumerate(gs['leaderboard'], 1):
        if entry['name'] == 'You':
            return i
    return '-'


def _derive_scenario(price_index, prev_price_index, rate):
    """Label the current macro environment from the data itself."""
    change = (price_index - prev_price_index) / max(prev_price_index, 1) * 100
    if change > 2.0:
        return 'Boom'
    if change < -1.5:
        return 'Correction' if rate > 3.0 else 'Crash'
    if rate > 8.0:
        return 'High Rates'
    if change > 0.5:
        return 'Recovery'
    return 'Baseline'


def _build_starting_mortgages(portfolio, rate, target_debt=200_000):
    """Create variable-rate mortgages distributed proportionally across starting properties."""
    total_value = sum(p['value'] for p in portfolio)
    effective_rate = round(rate + FIX_PREMIUMS['variable'], 2)
    mortgages = []
    for prop in portfolio:
        loan = int(prop['value'] / total_value * target_debt)
        if loan > 0:
            mortgages.append({
                'prop_id':        prop['id'],
                'loan':           loan,
                'rate_type':      'variable',
                'rate':           effective_rate,
                'fixed_rate':     None,
                'fix_expires_tick': None,
                'monthly_payment': round(loan * effective_rate / 100 / 12, 2),
            })
    return mortgages


def _stamped_portfolio(portfolio):
    """Set purchase_price = value on each property if not already set."""
    for p in portfolio:
        p.setdefault('purchase_price', p['value'])
    return portfolio


def init_game_state(total_ticks=20, archetype='balanced'):
    """Build a fresh GAME_STATE from START_STATE."""
    ss = dd.START_STATE
    player_actor = ss['actors'][0]
    ai_actors = ss['actors'][1:]

    total_ticks = total_ticks or ss['total_ticks']

    # Pick a random historical start period (hidden from player until game end)
    min_year, max_year = hist.get_start_limits(total_ticks)
    start_year = random.randint(min_year, max_year)
    start_half = random.choice([1, 2])
    # Ensure enough data remains
    while True:
        try:
            macro_slice = hist.get_slice(start_year, start_half, total_ticks)
            break
        except ValueError:
            start_half = 1
            start_year -= 1

    first = macro_slice[0]
    base_price_index = first[2]  # raw index value at start (used to normalise)
    starting_rate = first[3]
    starting_rent_growth = first[4]

    # Normalise price_index so the game always starts at 100.0
    price_scale = 100.0 / base_price_index

    # Fixed chart bounds: full game price-index range, rounded to nearest 5
    _all_pi = [entry[2] * price_scale for entry in macro_slice]
    price_chart_min = math.floor(min(_all_pi) / 5) * 5
    price_chart_max = math.ceil(max(_all_pi) / 5) * 5

    arc = SCENARIO_ARCS.get(total_ticks, SCENARIO_ARC_40)  # kept for advance_signal only

    player_portfolio = _stamped_portfolio(copy.deepcopy(player_actor['portfolio']))

    def _make_ai_entry(a):
        ai_portfolio = _stamped_portfolio(copy.deepcopy(a['portfolio']))
        return {
            'name': a['name'],
            'cash': a['cash'],
            'portfolio': ai_portfolio,
            'mortgages': _build_starting_mortgages(
                ai_portfolio, starting_rate, target_debt=200_000
            ),
            'portfolio_value': sum(p['value'] for p in a['portfolio']),
            'props': len(a['portfolio']),
            'last_action': 'hold',
            'last_property': None,
            'rationale': 'waiting to see how the market moves',
            'total_debt': 200_000,
            'cumulative_rent': 0,
        }

    gs = {
        'tick': 0,
        'total_ticks': total_ticks,
        'scenario_arc': arc,                     # synthetic arc retained for advance warnings
        'macro_slice': macro_slice,              # historical data; one entry per tick
        'price_scale': price_scale,              # normalisation factor
        'real_start_year': start_year,
        'real_start_half': start_half,
        'archetype': archetype if archetype in ARCHETYPE_META else 'balanced',
        'scenario': _derive_scenario(100.0, 100.0, starting_rate),
        'macro': {
            'price_index': 100.0,
            'rate': starting_rate,
            'rent_growth': starting_rent_growth,
            'prev': {'price_index': 100.0, 'rate': starting_rate, 'rent_growth': starting_rent_growth},
        },
        # Starting mortgages: ~£200k distributed proportionally across starting portfolio
        # at the historical starting rate (variable, no fix).
        'player': {
            'cash': player_actor['cash'],
            'portfolio': player_portfolio,
            'mortgages': _build_starting_mortgages(
                player_portfolio, starting_rate, target_debt=200_000
            ),
            'cumulative_rent': 0,
        },
        'ai': [_make_ai_entry(a) for a in ai_actors],
        'market': copy.deepcopy(ss['market']),
        'news': ['Market opens. Scenario: Baseline — Steady conditions. Good time to build positions.'],
        'leaderboard': [],
        'end': None,
        'next_prop_id': 100,
        'macro_history': [],
        'score_history': [],
        'price_chart_min': price_chart_min,
        'price_chart_max': price_chart_max,
        'reg_events_fired': [],   # list of event keys that have already fired
        'rent_freeze': {},        # {region_or_'ALL': ticks_remaining}
        'refinance_cooldown': 0,
    }
    update_leaderboard(gs)
    return gs


def apply_player_action(gs, action, buy_prop_id, sell_prop_id, ltv=0.0, rate_type='variable'):
    """Mutate gs in place for the player's chosen action."""
    player = gs['player']
    market = gs['market']
    year = current_real_year(gs)

    if action == 'buy' and buy_prop_id:
        prop = next((p for p in market if p['id'] == buy_prop_id), None)
        if prop:
            sdlt = calc_sdlt(prop['value'], year)
            loan = int(prop['value'] * ltv)
            deposit = prop['value'] - loan
            if player['cash'] >= deposit + sdlt:
                player['cash'] -= deposit + sdlt
                if loan > 0:
                    premium = FIX_PREMIUMS.get(rate_type, 0.0)
                    effective_rate = round(gs['macro']['rate'] + premium, 2)
                    monthly_payment = round((loan * effective_rate / 100) / 12, 2)
                    fix_expires = gs['tick'] + FIX_DURATIONS[rate_type] if rate_type in FIX_DURATIONS else None
                    player['mortgages'].append({
                        'prop_id': prop['id'],
                        'loan': loan,
                        'rate_type': rate_type,
                        'rate': effective_rate,
                        'fixed_rate': effective_rate if rate_type != 'variable' else None,
                        'fix_expires_tick': fix_expires,
                        'monthly_payment': monthly_payment,
                    })
                prop['purchase_price'] = prop['value']
                player['portfolio'].append(prop)
                market.remove(prop)

    elif action == 'sell' and sell_prop_id:
        prop = next((p for p in player['portfolio'] if p['id'] == sell_prop_id), None)
        if prop:
            mortgage = next((m for m in player['mortgages'] if m['prop_id'] == prop['id']), None)
            loan_repaid = mortgage['loan'] if mortgage else 0
            agent_fee = int(prop['value'] * AGENT_FEE_RATE)
            net_proceeds = max(0, prop['value'] - loan_repaid - agent_fee)
            player['cash'] += net_proceeds
            if mortgage:
                player['mortgages'].remove(mortgage)
            player['portfolio'].remove(prop)
            market.append(prop)

    elif action == 'remortgage' and buy_prop_id:
        if gs.get('refinance_cooldown', 0) > 0:
            gs['news'].append(f"Refinance unavailable — cooldown: {gs['refinance_cooldown']} turns remaining.")
            return
        prop = next((p for p in player['portfolio'] if p['id'] == buy_prop_id), None)
        if prop:
            new_loan = int(prop['value'] * min(ltv, 0.75))
            existing_m = next((m for m in player['mortgages'] if m['prop_id'] == prop['id']), None)
            existing_loan = existing_m['loan'] if existing_m else 0
            cash_released = new_loan - existing_loan
            premium = FIX_PREMIUMS.get(rate_type, 0.0)
            effective_rate = round(gs['macro']['rate'] + premium, 2)
            monthly_payment = round((new_loan * effective_rate / 100) / 12, 2)
            fix_expires = gs['tick'] + FIX_DURATIONS[rate_type] if rate_type in FIX_DURATIONS else None
            if cash_released > 0:
                player['cash'] += cash_released
            new_m = {
                'prop_id': prop['id'],
                'loan': new_loan,
                'rate_type': rate_type,
                'rate': effective_rate,
                'fixed_rate': effective_rate if rate_type != 'variable' else None,
                'fix_expires_tick': fix_expires,
                'monthly_payment': monthly_payment,
            }
            if existing_m:
                existing_m.update(new_m)
            else:
                player['mortgages'].append(new_m)
            gs['refinance_cooldown'] = 5
            equity_note = f', £{cash_released:,} equity released' if cash_released > 0 else ''
            gs['news'].append(
                f"Refinanced: {prop['id']} — {rate_type} at {effective_rate}%{equity_note}."
            )

    elif action == 'upgrade_epc' and buy_prop_id:
        prop = next((p for p in player['portfolio'] if p['id'] == buy_prop_id), None)
        if prop and not prop.get('epc_compliant', True) and player['cash'] >= EPC_UPGRADE_COST:
            player['cash'] -= EPC_UPGRADE_COST
            prop['epc_compliant'] = True
            gs['news'].append(f"EPC upgrade: {prop['id']} now compliant — full rent restored.")

    elif action == 'renovate' and buy_prop_id:
        prop = next((p for p in player['portfolio'] if p['id'] == buy_prop_id), None)
        if prop and not prop.get('renovated', False):
            cost = int(prop['value'] * 0.10)
            if player['cash'] >= cost:
                player['cash'] -= cost
                prop['rent'] = int(prop['rent'] * 1.15)
                prop['value'] = int(prop['value'] * 1.08)
                prop['renovated'] = True
                gs['news'].append(
                    f"Renovation: {prop['id']} — value +8%, rent +15%. Cost: £{cost:,}."
                )


_SELL_SCENARIOS = {'Correction', 'Crash'}


def _ai_sell_one(gs, ai):
    """Sell one AI property (closest to average value) back to the market. Returns sold value."""
    portfolio = ai.get('portfolio', [])
    if not portfolio:
        return 0
    avg = ai['portfolio_value'] / len(portfolio)
    prop = min(portfolio, key=lambda p: abs(p['value'] - avg))
    mortgage = next((m for m in ai.get('mortgages', []) if m['prop_id'] == prop['id']), None)
    loan = mortgage['loan'] if mortgage else 0
    net_proceeds = max(0, prop['value'] - loan)
    portfolio.remove(prop)
    if mortgage:
        ai['mortgages'].remove(mortgage)
    ai['cash'] += net_proceeds
    ai['total_debt'] = max(0, ai.get('total_debt', 0) - loan)
    ai['portfolio_value'] -= prop['value']
    ai['props'] -= 1
    gs['market'].append(prop)
    return prop['value']


_CAPITAL_MAX_RATE  = 7.0   # Mr Hugh Price pauses buying above this rate (selective — capital strategy)
_CAPITAL_FALL_TICKS = 2   # consecutive price falls before Mr Hugh Price sells
_LEVERAGE_BUY_RATE  = 9.0  # Mr Max Lever buys opportunistically in broad rate window
_LEVERAGE_SELL_RATE = 12.0  # Mr Max Lever only sells in extreme rate spike


def ai_decide(gs, ai):
    """Return (action, prop_or_None, rationale, ltv) for one AI actor."""
    market = gs['market']
    name = ai['name']
    macro = gs['macro']
    rate = macro['rate']
    history = gs.get('macro_history', [])

    if name == 'Mr Max Lever':
        # Sell when rates are critically high
        if rate > _LEVERAGE_SELL_RATE and ai['props'] > 0:
            return 'sell', None, f'selling — rate {rate}% exceeds stress threshold', 0.0
        # Buy at max leverage when rate is acceptable
        if rate <= _LEVERAGE_BUY_RATE:
            ltv = 0.75
            affordable = [p for p in market if not p.get('auction') and p['value'] * (1 - ltv) <= ai['cash']]
            if affordable:
                prop = max(affordable, key=lambda p: p['value'])
                return 'buy', prop, f'max leverage at {rate}% rate — highest value target', ltv
        return 'hold', None, f'holding — rate {rate}% above buy threshold', 0.0

    elif name == 'Mr Hugh Price':
        # Sell after sustained price falls (capital strategy — protect gains)
        if len(history) >= _CAPITAL_FALL_TICKS:
            falling = all(
                history[-(i + 1)]['price_index'] < history[-(i + 2)]['price_index']
                for i in range(_CAPITAL_FALL_TICKS)
                if len(history) > i + 1
            )
            if falling and ai['props'] > 0:
                return 'sell', None, 'prices falling for 2+ ticks — protecting capital', 0.0
        # Rate gate: capital gains evaporate with high mortgage costs
        if rate > _CAPITAL_MAX_RATE:
            return 'hold', None, f'holding — rate {rate}% above capital strategy threshold', 0.0
        ltv = 0.60
        # Target higher-value properties (capital growth focus)
        candidates = [p for p in market if not p.get('auction') and p['value'] * (1 - ltv) <= ai['cash']]
        if candidates:
            prop = max(candidates, key=lambda p: p['value'])
            return 'buy', prop, 'targeting highest value property for capital growth (60% LTV)', ltv
        return 'hold', None, 'no affordable properties at 60% LTV', 0.0

    return 'hold', None, 'holding position', 0.0


def apply_ai_actions(gs):
    """Apply AI decisions to the market and AI state. Returns list of action dicts."""
    results = []
    for ai in gs['ai']:
        action, prop, rationale, ltv = ai_decide(gs, ai)
        ai['last_action'] = action
        ai['rationale'] = rationale
        if action == 'buy' and prop:
            deposit = int(prop['value'] * (1 - ltv))
            loan = int(prop['value'] * ltv)
            effective_rate = round(gs['macro']['rate'] + FIX_PREMIUMS['variable'], 2)
            ai['cash'] -= deposit
            ai['total_debt'] = ai.get('total_debt', 0) + loan
            ai['portfolio_value'] += prop['value']
            ai['props'] += 1
            ai['last_property'] = prop['id']
            prop['purchase_price'] = prop['value']
            ai['portfolio'].append(prop)
            if loan > 0:
                ai['mortgages'].append({
                    'prop_id': prop['id'], 'loan': loan, 'rate_type': 'variable',
                    'rate': effective_rate, 'fixed_rate': None, 'fix_expires_tick': None,
                    'monthly_payment': round(loan * effective_rate / 100 / 12, 2),
                })
            gs['market'].remove(prop)
            results.append({'name': ai['name'], 'action': 'buy', 'prop': copy.copy(prop), 'rationale': rationale})
        elif action == 'sell':
            sold_value = _ai_sell_one(gs, ai)
            ai['last_property'] = f'£{sold_value:,}'
            results.append({'name': ai['name'], 'action': 'sell', 'prop': {'value': sold_value, 'id': '—'}, 'rationale': rationale})
        else:
            ai['last_property'] = None
            results.append({'name': ai['name'], 'action': action, 'prop': None, 'rationale': rationale})
    return results


def apply_regulatory_events(gs):
    """Fire one-shot regulatory events based on real year or random chance."""
    fired = gs.get('reg_events_fired', [])
    tick = gs['tick']
    year = current_real_year(gs)

    # EPC C requirement — fires when era reaches 2018 or randomly after tick 8
    if 'epc' not in fired:
        if year >= 2018 or (tick >= 8 and random.random() < 0.18):
            for prop in gs['player']['portfolio']:
                prop.setdefault('epc_compliant', True)
                prop['epc_compliant'] = False
            for prop in gs['market']:
                prop.setdefault('epc_compliant', True)
                prop['epc_compliant'] = False
            fired.append('epc')
            gs['news'].append(
                "! Regulation: EPC C requirement — non-compliant properties lose 15% rent until upgraded (£5,000 each)."
            )

    # Licensing scheme — random, fires once after tick 5
    if 'licensing' not in fired and tick >= 5 and random.random() < 0.08:
        region = random.choice(_REGIONS)
        affected = [p for p in gs['player']['portfolio'] if p.get('region') == region]
        cost = len(affected) * LICENSING_COST_PROP
        gs['player']['cash'] -= cost
        fired.append('licensing')
        gs['news'].append(
            f"! Regulation: {region} licensing scheme introduced — "
            f"£{LICENSING_COST_PROP:,}/property. You paid £{cost:,} for {len(affected)} properties."
        )

    # Rent freeze — random, fires once after tick 6
    if 'rent_freeze' not in fired and tick >= 6 and random.random() < 0.06:
        if random.random() < 0.35:
            gs['rent_freeze']['ALL'] = RENT_FREEZE_TURNS
            fired.append('rent_freeze')
            gs['news'].append(
                f"! Policy: National rent freeze — rent growth frozen for {RENT_FREEZE_TURNS} turns."
            )
        else:
            region = random.choice(_REGIONS)
            gs['rent_freeze'][region] = RENT_FREEZE_TURNS
            fired.append('rent_freeze')
            gs['news'].append(
                f"! Policy: Rent freeze in {region} — rent growth frozen for {RENT_FREEZE_TURNS} turns."
            )

    gs['reg_events_fired'] = fired


def advance_tick(gs):
    """Apply rent income, growth, update tick. Returns True if game ended."""
    # Remove auction properties from previous turn (they last exactly one turn)
    gs['market'] = [p for p in gs['market'] if not p.get('auction', False)]

    apply_regulatory_events(gs)

    tick = gs['tick']  # current tick BEFORE increment

    # --- Pull this tick's macro from historical data ---
    macro_slice = gs['macro_slice']
    price_scale = gs['price_scale']
    entry = macro_slice[tick]          # (year, half, price_index, rate, rent_growth)
    next_entry = macro_slice[tick + 1] if tick + 1 < len(macro_slice) else entry

    raw_price_now  = entry[2] * price_scale
    raw_price_next = next_entry[2] * price_scale
    quarterly_growth = (raw_price_next - raw_price_now) / raw_price_now if raw_price_now else 0.0

    player = gs['player']

    # Update variable mortgage rates and check fix expiry BEFORE collecting rent
    current_rate = gs['macro']['rate']
    for mortgage in player.get('mortgages', []):
        rt = mortgage.get('rate_type', 'variable')
        expires = mortgage.get('fix_expires_tick')
        var_rate = round(current_rate + FIX_PREMIUMS['variable'], 2)
        if rt != 'variable' and expires and tick >= expires:
            mortgage['rate_type'] = 'variable'
            mortgage['rate'] = var_rate
            mortgage['fixed_rate'] = None
            mortgage['fix_expires_tick'] = None
            mortgage['monthly_payment'] = round((mortgage['loan'] * var_rate / 100) / 12, 2)
            gs['news'].append(
                f"! {mortgage['prop_id']} fix expired — reverted to variable ({var_rate}%)."
            )
        elif rt == 'variable':
            mortgage['rate'] = var_rate
            mortgage['monthly_payment'] = round((mortgage['loan'] * var_rate / 100) / 12, 2)

    # Player: rent income for 3 months (quarterly)
    _apply_void_risk(gs)
    rent_income = sum(
        int(p['rent'] * (1 - EPC_RENT_PENALTY) if not p.get('epc_compliant', True) else p['rent'])
        for p in player['portfolio']
        if not p.get('vacant', False)
    ) * 6
    player['cash'] += rent_income
    player['cumulative_rent'] = player.get('cumulative_rent', 0) + rent_income

    # Player: mortgage payments for 3 months (interest-only, quarterly)
    # Surcharge: individual property LTV > 65% of current value incurs extra 1.5% annual interest
    prop_values = {p['id']: p['value'] for p in player['portfolio']}
    for mortgage in player.get('mortgages', []):
        player['cash'] -= mortgage['monthly_payment'] * 6
        prop_val = prop_values.get(mortgage['prop_id'], 0)
        if prop_val > 0 and mortgage['loan'] / prop_val > 0.65:
            player['cash'] -= int(mortgage['loan'] * 0.015 / 12 * 6)

    # Player: property value growth — era-aware regional rates
    year = current_real_year(gs)
    rent_freeze = gs.get('rent_freeze', {})
    for p in player['portfolio']:
        gf = regional_hpi.get_regional_multiplier(year, p.get('region', 'West'))
        rg = quarterly_growth * gf
        p['value'] = int(p['value'] * (1 + rg))
        region = p.get('region', 'West')
        if not (rent_freeze.get('ALL', 0) > 0 or rent_freeze.get(region, 0) > 0):
            p['rent'] = int(p['rent'] * (1 + rg * 0.5))

    # Market: property value growth — era-aware regional rates
    for p in gs['market']:
        gf = regional_hpi.get_regional_multiplier(year, p.get('region', 'West'))
        rg = quarterly_growth * gf
        p['value'] = int(p['value'] * (1 + rg))
        p['rent'] = int(p['rent'] * (1 + rg * 0.5))

    # AI: per-property growth + rent income + mortgage payments (same model as player)
    for ai in gs['ai']:
        # Update variable mortgage rates
        for mortgage in ai.get('mortgages', []):
            if mortgage.get('rate_type', 'variable') == 'variable':
                var_rate = round(current_rate + FIX_PREMIUMS['variable'], 2)
                mortgage['rate'] = var_rate
                mortgage['monthly_payment'] = round(mortgage['loan'] * var_rate / 100 / 12, 2)

        # Rent income (6 months)
        ai_rent = sum(p['rent'] * 6 for p in ai.get('portfolio', []))
        ai['cash'] += ai_rent
        ai['cumulative_rent'] = ai.get('cumulative_rent', 0) + ai_rent

        # Per-property value and rent growth using same regional HPI as player
        for p in ai.get('portfolio', []):
            gf = regional_hpi.get_regional_multiplier(year, p.get('region', 'West'))
            rg = quarterly_growth * gf
            p['value'] = int(p['value'] * (1 + rg))
            p['rent'] = int(p['rent'] * (1 + rg * 0.5))

        # Recompute derived aggregate fields
        ai['portfolio_value'] = sum(p['value'] for p in ai.get('portfolio', []))
        ai['props'] = len(ai.get('portfolio', []))
        ai['total_debt'] = sum(m['loan'] for m in ai.get('mortgages', []))

        # Mortgage interest payments (6 months)
        ai['cash'] -= int(sum(m['monthly_payment'] * 6 for m in ai.get('mortgages', [])))

    # Macro: advance to next entry's values
    prev = {
        'price_index': gs['macro']['price_index'],
        'rate': gs['macro']['rate'],
        'rent_growth': gs['macro']['rent_growth'],
    }
    gs['macro']['price_index'] = round(raw_price_next, 1)
    gs['macro']['rate'] = next_entry[3]
    gs['macro']['rent_growth'] = next_entry[4]
    gs['macro']['prev'] = prev

    new_scenario = _derive_scenario(raw_price_next, raw_price_now, next_entry[3])
    if new_scenario != gs['scenario']:
        gs['news'].append(f">> Conditions shift: {new_scenario}")
        gs['scenario'] = new_scenario

    gs['tick'] += 1
    new_tick = gs['tick']

    # Decrement refinance cooldown
    if gs.get('refinance_cooldown', 0) > 0:
        gs['refinance_cooldown'] -= 1

    # Decrement rent freeze counters
    rent_freeze = gs.get('rent_freeze', {})
    for k in list(rent_freeze.keys()):
        rent_freeze[k] -= 1
        if rent_freeze[k] <= 0:
            del rent_freeze[k]
            label = 'nationally' if k == 'ALL' else f'in {k}'
            gs['news'].append(f">> Rent freeze lifted {label} — rent growth resumes.")
    gs['rent_freeze'] = rent_freeze

    # Policy event: SDLT surcharge introduction (April 2016)
    if new_tick < len(macro_slice):
        prev_year = macro_slice[new_tick - 1][0]
        curr_year = macro_slice[new_tick][0]
        if prev_year < 2016 <= curr_year:
            gs['news'].append(
                "! Policy: 3% SDLT surcharge introduced on investment property purchases."
            )

    # Forced sale if player cash < -£50,000
    if player['cash'] < -50000 and player['portfolio']:
        cheapest = min(player['portfolio'], key=lambda p: p['value'])
        mortgage = next((m for m in player['mortgages'] if m['prop_id'] == cheapest['id']), None)
        loan_repaid = mortgage['loan'] if mortgage else 0
        net_proceeds = max(0, cheapest['value'] - loan_repaid)
        player['cash'] += net_proceeds
        if mortgage:
            player['mortgages'].remove(mortgage)
        player['portfolio'].remove(cheapest)
        gs['market'].append(cheapest)
        gs['news'].append(f"! Forced sale: {cheapest['id']} sold to cover cash shortfall.")

    # Fresh listings arrive each tick
    replenish_market(gs, count=2)

    # Add auction property every 8 ticks
    if new_tick % 8 == 0 and new_tick > 0:
        _add_auction_property(gs)

    update_leaderboard(gs)

    gs['macro_history'].append({
        'tick': new_tick,
        'price_index': gs['macro']['price_index'],
        'rate': gs['macro']['rate'],
        'rent_growth': gs['macro']['rent_growth'],
    })
    _ACTOR_ORDER = ['You', 'Mr Hugh Price', 'Mr Max Lever']
    lb_map = {e['name']: e['score'] for e in gs['leaderboard']}
    gs['score_history'].append({
        'tick': new_tick,
        'scores': [{'name': n, 'score': lb_map.get(n, 0)} for n in _ACTOR_ORDER],
    })

    if new_tick >= gs['total_ticks']:
        _build_end_state(gs)
        return True
    return False


def _build_end_state(gs):
    player = gs['player']
    portfolio_val = sum(p['value'] for p in player['portfolio'])
    rent_total = player.get('cumulative_rent', 0)
    archetype = gs.get('archetype', 'balanced')
    final_score = score_for_archetype(
        archetype, portfolio_val, player['cash'], rent_total,
        sum(m['loan'] for m in player.get('mortgages', [])),
        concentration_pen=concentration_penalty(player['portfolio']),
    )

    start_year = gs['real_start_year']
    start_half = gs['real_start_half']
    end_entry = gs['macro_slice'][-1]
    end_year = end_entry[0]
    end_half = end_entry[1]
    era_label = hist.get_era_label(start_year)
    min_year, max_year = hist.get_start_limits(gs['total_ticks'])

    gs['end'] = {
        'player_breakdown': {
            'portfolio': portfolio_val,
            'cash': player['cash'],
            'rent': rent_total,
            'final_score': final_score,
            'archetype': archetype,
            'archetype_label': ARCHETYPE_META[archetype]['label'],
            'archetype_desc': ARCHETYPE_META[archetype]['desc'],
        },
        'key_events': [
            {'tick': 1, 'text': 'Game started'},
            {'tick': gs['tick'], 'text': 'Game complete — final scores tallied'},
        ],
        'era_reveal': {
            'start_year': start_year,
            'start_half': start_half,
            'end_year': end_year,
            'end_half': end_half,
            'era_label': era_label,
            'limits': (min_year, max_year),
        },
    }


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

_ACTOR_COLORS = {'You': '#00FF88', 'Mr Hugh Price': '#FBBF24', 'Mr Max Lever': '#F87171'}


def sparkline_points(values, width=100, height=30, padding=3):
    """Generate SVG polyline points scaled to a fixed viewBox of width x height."""
    if len(values) < 2:
        return ''
    min_v = min(values)
    max_v = max(values)
    rng = max_v - min_v or 1
    pts = []
    for i, v in enumerate(values):
        x = padding + (i / (len(values) - 1)) * (width - 2 * padding)
        y = padding + (1 - (v - min_v) / rng) * (height - 2 * padding)
        pts.append(f'{x:.1f},{y:.1f}')
    return ' '.join(pts)


def build_chart_data(gs):
    macro_hist = gs.get('macro_history', [])
    sparklines = {
        'price': sparkline_points([h['price_index'] for h in macro_hist]),
        'rate':  sparkline_points([h['rate']        for h in macro_hist]),
        'rent':  sparkline_points([h['rent_growth'] for h in macro_hist]),
    }
    score_bars = []
    for entry in gs.get('score_history', []):
        total = sum(s['score'] for s in entry['scores']) or 1
        segments = [
            {
                'name':  s['name'],
                'pct':   round(s['score'] / total * 100, 1),
                'score': s['score'],
                'color': _ACTOR_COLORS.get(s['name'], '#888'),
            }
            for s in entry['scores']
        ]
        score_bars.append({'tick': entry['tick'], 'segments': segments})
    return sparklines, score_bars


# ---------------------------------------------------------------------------
# Template filters
# ---------------------------------------------------------------------------

@app.template_filter('currency')
def currency_filter(value):
    return f'${value:,.0f}'


@app.template_filter('pct')
def pct_filter(value):
    return f'{value:.1f}%'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def opening():
    ss = dd.START_STATE
    player = ss['actors'][0]
    return render_template(
        'opening.html',
        actors=ss['actors'],
        macro=ss['macro'],
        market=ss['market'],
        player=player,
    )


@app.route('/start', methods=['POST'])
def start():
    global GAME_STATE
    try:
        total_ticks = int(request.form.get('total_ticks', 40))
    except ValueError:
        total_ticks = 40
    if total_ticks not in (40, 80):
        total_ticks = 40
    archetype = request.form.get('archetype', 'balanced')
    if archetype not in ARCHETYPE_META:
        archetype = 'balanced'
    GAME_STATE = init_game_state(total_ticks=total_ticks, archetype=archetype)
    return redirect(url_for('turn'))


@app.route('/turn')
def turn():
    gs = GAME_STATE
    if not gs:
        return redirect(url_for('opening'))

    macro = gs['macro']
    trend = {
        'price_index': trend_symbol(macro['price_index'], macro['prev']['price_index']),
        'rate': trend_symbol(macro['rate'], macro['prev']['rate']),
        'rent_growth': trend_symbol(macro['rent_growth'], macro['prev']['rent_growth']),
    }
    portfolio_value = sum(p['value'] for p in gs['player']['portfolio'])
    player = gs['player']
    total_debt = sum(m['loan'] for m in player.get('mortgages', []))
    lev_pen = leverage_penalty(portfolio_value, total_debt)
    con_pen = concentration_penalty(player['portfolio'])
    rank = get_player_rank(gs)
    player_score_val = next(
        (e['score'] for e in gs['leaderboard'] if e['name'] == 'You'), 0
    )
    news = gs['news'][-2:] if len(gs['news']) > 2 else gs['news']
    phase = get_scenario_phase(gs['tick'], gs['scenario_arc'])
    scenario_desc = phase[3]
    sparklines, score_bars = build_chart_data(gs)

    archetype_meta = ARCHETYPE_META.get(gs.get('archetype', 'balanced'), ARCHETYPE_META['balanced'])

    year = current_real_year(gs)
    prev_pi = macro['prev']['price_index']
    nat_growth = (
        (macro['price_index'] - prev_pi) / prev_pi * 100
        if prev_pi else 0.0
    )
    regional_growths = {
        r: round(nat_growth * regional_hpi.get_regional_multiplier(year, r), 2)
        for r in ['London', 'South', 'East', 'West', 'Midlands', 'North', 'Scotland', 'Wales']
    }

    return render_template(
        'turn.html',
        gs=gs,
        macro=macro,
        trend=trend,
        portfolio_value=portfolio_value,
        rank=rank,
        player_score=player_score_val,
        leverage_pen=lev_pen,
        concentration_pen=con_pen,
        news=news,
        scenario_desc=scenario_desc,
        sparklines=sparklines,
        score_bars=score_bars,
        archetype_meta=archetype_meta,
        reg_events_fired=gs.get('reg_events_fired', []),
        rent_freeze=gs.get('rent_freeze', {}),
        regional_growths=regional_growths,
        national_growth=round(nat_growth, 2),
        macro_history=gs.get('macro_history', []),
        price_chart_min=gs.get('price_chart_min', 80),
        price_chart_max=gs.get('price_chart_max', 120),
    )


@app.route('/decision')
def decision():
    gs = GAME_STATE
    if not gs:
        return redirect(url_for('opening'))

    macro = gs['macro']
    trend = {
        'price_index': trend_symbol(macro['price_index'], macro['prev']['price_index']),
        'rate': trend_symbol(macro['rate'], macro['prev']['rate']),
        'rent_growth': trend_symbol(macro['rent_growth'], macro['prev']['rent_growth']),
    }
    rank = get_player_rank(gs)
    player_score_val = next(
        (e['score'] for e in gs['leaderboard'] if e['name'] == 'You'), 0
    )
    year = current_real_year(gs)
    market_with_yield = [
        {**p, 'yield_pct': gross_yield(p), 'sdlt': calc_sdlt(p['value'], year)}
        for p in gs['market']
    ]
    portfolio_with_yield = [
        {**p, 'yield_pct': gross_yield(p)} for p in gs['player']['portfolio']
    ]
    phase = get_scenario_phase(gs['tick'], gs['scenario_arc'])
    scenario_desc = phase[3]

    archetype_meta = ARCHETYPE_META.get(gs.get('archetype', 'balanced'), ARCHETYPE_META['balanced'])
    auction_props = [p for p in gs['market'] if p.get('auction')]
    return render_template(
        'decision.html',
        gs=gs,
        macro=macro,
        trend=trend,
        rank=rank,
        player_score=player_score_val,
        market=market_with_yield,
        portfolio=portfolio_with_yield,
        scenario_desc=scenario_desc,
        region_profiles=REGION_PROFILES,
        archetype_meta=archetype_meta,
        current_year=year,
        fix_premiums=FIX_PREMIUMS,
        reg_events_fired=gs.get('reg_events_fired', []),
        rent_freeze=gs.get('rent_freeze', {}),
        EPC_UPGRADE_COST=EPC_UPGRADE_COST,
        refinance_cooldown=gs.get('refinance_cooldown', 0),
        auction_props=auction_props,
    )


@app.route('/decision/confirm', methods=['POST'])
def decision_confirm():
    global GAME_STATE
    gs = GAME_STATE
    if not gs:
        return redirect(url_for('opening'))

    action = request.form.get('action', 'hold')
    buy_prop_id = request.form.get('buy_prop_id', '')
    sell_prop_id = request.form.get('sell_prop_id', '')
    ltv_str = request.form.get('ltv', '0')
    try:
        ltv = float(ltv_str)
    except ValueError:
        ltv = 0.0

    # 1. Snapshot player action for summary display
    player_prop = None
    if action == 'buy' and buy_prop_id:
        player_prop = next((p for p in gs['market'] if p['id'] == buy_prop_id), None)
    elif action == 'sell' and sell_prop_id:
        player_prop = next((p for p in gs['player']['portfolio'] if p['id'] == sell_prop_id), None)
    player_summary = {'action': action, 'prop': copy.copy(player_prop) if player_prop else None}

    rate_type = request.form.get('rate_type', 'variable')
    if rate_type not in FIX_PREMIUMS:
        rate_type = 'variable'

    # Handle auction bid (resolved before regular AI actions)
    auction_prop_id = request.form.get('auction_prop_id', '')
    try:
        auction_bid_amount = int(request.form.get('auction_bid', 0) or 0)
    except ValueError:
        auction_bid_amount = 0
    if action == 'auction_bid' and auction_prop_id:
        auction_prop = next(
            (p for p in gs['market'] if p.get('id') == auction_prop_id and p.get('auction')),
            None
        )
        if auction_prop:
            _resolve_auction(gs, auction_prop, player_bid=auction_bid_amount, ltv=ltv, rate_type=rate_type)
        action = 'hold'
        buy_prop_id = ''

    # 2. Apply player action
    apply_player_action(gs, action, buy_prop_id, sell_prop_id, ltv=ltv, rate_type=rate_type)

    # 3. AI decisions
    ai_summaries = apply_ai_actions(gs)

    # 4. Store round summary for display
    gs['last_round'] = {'player': player_summary, 'ai': ai_summaries, 'tick': gs['tick']}

    # 5. Advance tick
    game_over = advance_tick(gs)
    gs['game_over'] = game_over

    return redirect(url_for('round_summary'))


@app.route('/round-summary')
def round_summary():
    gs = GAME_STATE
    if not gs or 'last_round' not in gs:
        return redirect(url_for('turn'))
    rank = get_player_rank(gs)
    player_score_val = next((e['score'] for e in gs['leaderboard'] if e['name'] == 'You'), 0)
    next_url = url_for('end') if gs.get('game_over') else None
    _, score_bars = build_chart_data(gs)
    return render_template('round_summary.html', gs=gs, round=gs['last_round'],
                           rank=rank, player_score=player_score_val, next_url=next_url,
                           score_bars=score_bars)


@app.route('/end')
def end():
    gs = GAME_STATE
    if not gs or not gs.get('end'):
        return redirect(url_for('opening'))
    return render_template('end.html', gs=gs)


@app.route('/play-again', methods=['POST'])
def play_again():
    global GAME_STATE
    GAME_STATE = {}
    return redirect(url_for('opening'))


if __name__ == '__main__':
    app.run(debug=True, port=5050)
