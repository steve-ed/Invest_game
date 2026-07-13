# Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-width analytics panel to `turn.html` showing 9 portfolio metrics side-by-side for the player and all AI actors.

**Architecture:** `purchase_price` is stamped onto each property dict at acquisition. A new `compute_analytics(gs)` function in `app.py` computes all 9 metrics for every actor and returns a dict keyed by name. The `/turn` route passes this dict to `turn.html`, which renders it as a styled table.

**Tech Stack:** Python 3, Flask, Jinja2, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ui_web/app.py` | Modify | Stamp `purchase_price` at buy; add `compute_analytics(gs)`; pass to `/turn` route |
| `ui_web/templates/turn.html` | Modify | Add analytics panel below main content |
| `tests/test_analytics.py` | Create | Unit tests for `compute_analytics` and `purchase_price` stamping |

---

## Task 1: Stamp `purchase_price` on property acquisition

**Files:**
- Modify: `ui_web/app.py` (lines 382–471 `init_game_state`, line 504 `apply_player_action`, line 667 `apply_ai_actions`)
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_analytics.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app
from unittest.mock import patch


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
    # Force Mr Max Lever to buy (set low rate, give cash)
    gs['macro']['rate'] = 3.0
    ai = next(a for a in gs['ai'] if a['name'] == 'Mr Max Lever')
    ai['cash'] = 500_000
    market_before = [p['id'] for p in gs['market']]
    with patch('random.random', return_value=1.0):
        web_app.apply_ai_actions(gs)
    new_props = [p for p in ai['portfolio'] if p['id'] not in
                 [pp['id'] for pp in web_app.dd.START_STATE['actors'][2]['portfolio']]]
    # Only check if a buy actually happened
    bought_props = [p for p in ai['portfolio'] if p['id'] in market_before]
    for p in bought_props:
        assert 'purchase_price' in p, f"AI bought property {p['id']} missing purchase_price"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd C:\Users\steve\projects\realestgame-v2
python -m pytest tests/test_analytics.py -v
```

Expected: `test_starting_player_portfolio_has_purchase_price` and `test_starting_ai_portfolio_has_purchase_price` FAIL with `AssertionError: Property ... missing purchase_price`.

- [ ] **Step 3: Stamp `purchase_price` in `init_game_state()`**

In `ui_web/app.py`, find `init_game_state()` (~line 379). The player portfolio is deep-copied at line 435 and AI portfolios at line 445. Add stamping immediately after each deep copy.

Replace lines 433–456:

```python
        player_portfolio = copy.deepcopy(player_actor['portfolio'])
        for p in player_portfolio:
            p['purchase_price'] = p['value']
        'player': {
            'cash': player_actor['cash'],
            'portfolio': player_portfolio,
            'mortgages': _build_starting_mortgages(
                player_portfolio, starting_rate, target_debt=200_000
            ),
            'cumulative_rent': 0,
        },
        'ai': [
            {
                'name': a['name'],
                'cash': a['cash'],
                'portfolio': _stamped_portfolio(copy.deepcopy(a['portfolio'])),
                'mortgages': _build_starting_mortgages(
                    copy.deepcopy(a['portfolio']), starting_rate, target_debt=200_000
                ),
                'portfolio_value': sum(p['value'] for p in a['portfolio']),
                'props': len(a['portfolio']),
                'last_action': 'hold',
                'last_property': None,
                'rationale': 'waiting to see how the market moves',
                'total_debt': 200_000,
                'cumulative_rent': 0,
            }
            for a in ai_actors
        ],
```

Add this helper function just above `init_game_state()` (~line 379):

```python
def _stamped_portfolio(portfolio):
    """Set purchase_price = value on each property if not already set."""
    for p in portfolio:
        p.setdefault('purchase_price', p['value'])
    return portfolio
```

Then update the player portfolio assignment to use the helper too. The full block in `init_game_state()` at lines 433–457 should become:

```python
        player_portfolio = _stamped_portfolio(copy.deepcopy(player_actor['portfolio']))
        'player': {
            'cash': player_actor['cash'],
            'portfolio': player_portfolio,
            'mortgages': _build_starting_mortgages(
                player_portfolio, starting_rate, target_debt=200_000
            ),
            'cumulative_rent': 0,
        },
        'ai': [
            {
                'name': a['name'],
                'cash': a['cash'],
                'portfolio': _stamped_portfolio(copy.deepcopy(a['portfolio'])),
                'mortgages': _build_starting_mortgages(
                    copy.deepcopy(a['portfolio']), starting_rate, target_debt=200_000
                ),
                'portfolio_value': sum(p['value'] for p in a['portfolio']),
                'props': len(a['portfolio']),
                'last_action': 'hold',
                'last_property': None,
                'rationale': 'waiting to see how the market moves',
                'total_debt': 200_000,
                'cumulative_rent': 0,
            }
            for a in ai_actors
        ],
```

- [ ] **Step 4: Stamp `purchase_price` in `apply_player_action()` on buy**

In `apply_player_action()` (~line 504), find:

```python
                player['portfolio'].append(prop)
                market.remove(prop)
```

Replace with:

```python
                prop['purchase_price'] = prop['value']
                player['portfolio'].append(prop)
                market.remove(prop)
```

- [ ] **Step 5: Stamp `purchase_price` in `apply_ai_actions()` on buy**

In `apply_ai_actions()` (~line 667), find:

```python
            ai['portfolio'].append(prop)
```

Replace with:

```python
            prop['purchase_price'] = prop['value']
            ai['portfolio'].append(prop)
```

- [ ] **Step 6: Run tests to confirm they pass**

```
python -m pytest tests/test_analytics.py::test_starting_player_portfolio_has_purchase_price tests/test_analytics.py::test_starting_ai_portfolio_has_purchase_price tests/test_analytics.py::test_player_buy_stamps_purchase_price -v
```

Expected: all 3 PASS.

- [ ] **Step 7: Run full suite to catch regressions**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Fix any failures before continuing.

- [ ] **Step 8: Commit**

```bash
git add ui_web/app.py tests/test_analytics.py
git commit -m "feat: stamp purchase_price on properties at acquisition"
```

---

## Task 2: Add `compute_analytics(gs)` function

**Files:**
- Modify: `ui_web/app.py` (add function after `update_leaderboard`)
- Modify: `tests/test_analytics.py` (add tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_analytics.py`:

```python
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
    if not portfolio:
        return
    annual_rent = sum(p['rent'] * 12 for p in portfolio)
    portfolio_value = sum(p['value'] for p in portfolio)
    expected = round(annual_rent / portfolio_value * 100, 1)
    assert result['You']['gross_yield'] == expected


def test_compute_analytics_unrealised():
    gs = _make_gs()
    # Manually inflate one property value to create known unrealised gain
    p = gs['player']['portfolio'][0]
    p['purchase_price'] = p['value']
    p['value'] = p['value'] + 10_000
    result = web_app.compute_analytics(gs)
    unrealised = result['You']['unrealised']
    assert unrealised >= 10_000


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
    # Force one property non-compliant
    if gs['player']['portfolio']:
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
```

- [ ] **Step 2: Run to confirm they fail**

```
python -m pytest tests/test_analytics.py -v -k "compute_analytics"
```

Expected: all FAIL with `AttributeError: module 'app' has no attribute 'compute_analytics'`.

- [ ] **Step 3: Implement `compute_analytics(gs)`**

Add this function to `ui_web/app.py` directly after `update_leaderboard()` (~line 213):

```python
def _actor_analytics(portfolio, mortgages, cash):
    """Compute all 9 analytics metrics for one actor."""
    if not portfolio:
        return {
            'gross_yield': 0.0, 'unrealised': 0, 'roe': 0.0,
            'coc_return': 0.0, 'avg_cap_gr': 0.0, 'refi_headrm': 0.0,
            'epc_count': 0, 'epc_value': 0, 'region_conc': 0.0, 'cash': cash,
        }

    portfolio_value = sum(p['value'] for p in portfolio)
    annual_rent = sum(p['rent'] * 12 for p in portfolio)
    total_debt = sum(m['loan'] for m in mortgages)
    equity = portfolio_value - total_debt

    # GROSS YIELD
    gross_yield = round(annual_rent / portfolio_value * 100, 1) if portfolio_value else 0.0

    # UNREALISED
    unrealised = sum(p['value'] - p.get('purchase_price', p['value']) for p in portfolio)

    # ROE
    roe = round(annual_rent / equity * 100, 1) if equity > 0 else 0.0

    # COC RETURN (deposit approximated as 25% of purchase_price)
    total_deposits = sum(p.get('purchase_price', p['value']) * 0.25 for p in portfolio)
    coc_return = round(annual_rent / total_deposits * 100, 1) if total_deposits > 0 else 0.0

    # AVG CAP GR
    cap_growths = [
        (p['value'] - p.get('purchase_price', p['value'])) / p.get('purchase_price', p['value']) * 100
        for p in portfolio
        if p.get('purchase_price', p['value']) > 0
    ]
    avg_cap_gr = round(sum(cap_growths) / len(cap_growths), 1) if cap_growths else 0.0

    # REFI HEADROOM
    refi_headrm = portfolio_value * 0.75 - total_debt

    # EPC RISK
    non_compliant = [p for p in portfolio if not p.get('epc_compliant', True)]
    epc_count = len(non_compliant)
    epc_value = sum(p['value'] for p in non_compliant)

    # REGION CONC
    region_totals = {}
    for p in portfolio:
        r = p.get('region', 'West')
        region_totals[r] = region_totals.get(r, 0) + p['value']
    region_conc = round(max(region_totals.values()) / portfolio_value * 100, 1) if region_totals else 0.0

    return {
        'gross_yield': gross_yield,
        'unrealised': int(unrealised),
        'roe': roe,
        'coc_return': coc_return,
        'avg_cap_gr': avg_cap_gr,
        'refi_headrm': refi_headrm,
        'epc_count': epc_count,
        'epc_value': epc_value,
        'region_conc': region_conc,
        'cash': cash,
    }


def compute_analytics(gs):
    """Return analytics dict keyed by actor name for player and all AIs."""
    player = gs['player']
    result = {
        'You': _actor_analytics(
            player['portfolio'], player.get('mortgages', []), player['cash']
        )
    }
    for ai in gs['ai']:
        result[ai['name']] = _actor_analytics(
            ai.get('portfolio', []), ai.get('mortgages', []), ai['cash']
        )
    return result
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_analytics.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest tests/ --tb=short 2>&1 | tail -20
```

Fix any failures before continuing.

- [ ] **Step 6: Commit**

```bash
git add ui_web/app.py tests/test_analytics.py
git commit -m "feat: add compute_analytics function for per-actor portfolio metrics"
```

---

## Task 3: Pass analytics to the `/turn` route

**Files:**
- Modify: `ui_web/app.py` (`/turn` route, lines 1062–1123)

- [ ] **Step 1: Add `analytics` to the turn route**

In the `/turn` route function (`ui_web/app.py` ~line 1101), find the `return render_template(` call and add one line:

```python
    analytics = compute_analytics(gs)

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
        analytics=analytics,
    )
```

- [ ] **Step 2: Smoke test the route loads without error**

```
cd ui_web && python app.py
```

Navigate to http://localhost:5050, start a game, confirm the turn page loads without a 500 error. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add ui_web/app.py
git commit -m "feat: pass analytics dict to turn template"
```

---

## Task 4: Add analytics panel to `turn.html`

**Files:**
- Modify: `ui_web/templates/turn.html` (insert before `</div>` closing the main content column, around line 340)

- [ ] **Step 1: Add CSS for analytics table**

In `turn.html`, find the `<style>` block (near the top). Add these rules inside it:

```css
.analytics-panel { margin-top: 18px; }
.analytics-table { width: 100%; border-collapse: collapse; font-size: 0.82em; }
.analytics-table th { color: var(--muted); font-weight: normal; font-size: 0.85em;
                      letter-spacing: 0.06em; padding: 4px 10px 6px; text-align: right; }
.analytics-table th:first-child { text-align: left; }
.analytics-table td { padding: 3px 10px; text-align: right; border-top: 1px solid var(--border); }
.analytics-table td:first-child { text-align: left; color: var(--muted);
                                   font-size: 0.8em; letter-spacing: 0.08em; }
.analytics-table tr:hover td { background: rgba(255,255,255,0.03); }
.val-green { color: #00FF88; }
.val-red   { color: #F87171; }
.val-neutral { color: var(--text); }
```

- [ ] **Step 2: Add analytics panel HTML**

In `turn.html`, find the line:

```html
      <a href="/decision" class="btn btn-large" id="decision-btn">&gt;&gt; MAKE DECISION</a>
```

Insert the analytics panel **immediately before** that line:

```html
    <!-- Analytics Dashboard -->
    <div class="panel analytics-panel">
      <div class="panel-title">ANALYTICS</div>
      {% set actors = ['You'] + gs.ai | map(attribute='name') | list %}
      {% set actor_colours = {
          'You': '#00FF88',
          'Mr Hugh Price': '#FBBF24',
          'Mr Max Lever': '#F87171'
      } %}
      <table class="analytics-table">
        <thead>
          <tr>
            <th></th>
            {% for actor in actors %}
            <th style="color: {{ actor_colours.get(actor, 'var(--text)') }};">
              {{ actor }}
            </th>
            {% endfor %}
          </tr>
        </thead>
        <tbody>

          {# GROSS YIELD #}
          <tr>
            <td>GROSS YIELD</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-green">{{ a.gross_yield }}%</td>
            {% endfor %}
          </tr>

          {# UNREALISED #}
          <tr>
            <td>UNREALISED</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="{{ 'val-green' if a.unrealised >= 0 else 'val-red' }}">
              {% if a.unrealised >= 0 %}+{% endif %}{{ (a.unrealised | abs) | currency if a.unrealised != 0 else '£0' }}
            </td>
            {% endfor %}
          </tr>

          {# ROE #}
          <tr>
            <td>ROE</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-green">{{ a.roe }}%</td>
            {% endfor %}
          </tr>

          {# COC RETURN #}
          <tr>
            <td>COC RETURN</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-green">{{ a.coc_return }}%</td>
            {% endfor %}
          </tr>

          {# AVG CAP GR #}
          <tr>
            <td>AVG CAP GR</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="{{ 'val-green' if a.avg_cap_gr >= 0 else 'val-red' }}">
              {% if a.avg_cap_gr >= 0 %}+{% endif %}{{ a.avg_cap_gr }}%
            </td>
            {% endfor %}
          </tr>

          {# REFI HEADRM #}
          <tr>
            <td>REFI HEADRM</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-neutral">{{ a.refi_headrm | int | currency }}</td>
            {% endfor %}
          </tr>

          {# EPC RISK #}
          <tr>
            <td>EPC RISK</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="{{ 'val-red' if a.epc_count > 0 else 'val-green' }}">
              {% if a.epc_count > 0 %}
                {{ a.epc_count }} &middot; {{ a.epc_value | currency }}
              {% else %}
                None
              {% endif %}
            </td>
            {% endfor %}
          </tr>

          {# REGION CONC #}
          <tr>
            <td>REGION CONC</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-neutral">{{ a.region_conc }}%</td>
            {% endfor %}
          </tr>

          {# CASH #}
          <tr>
            <td>CASH</td>
            {% for actor in actors %}{% set a = analytics[actor] %}
            <td class="val-neutral">{{ a.cash | currency }}</td>
            {% endfor %}
          </tr>

        </tbody>
      </table>
    </div>
```

- [ ] **Step 3: Verify `currency` filter exists in app.py**

```
grep -n "currency" ui_web/app.py | head -5
```

Expected: a Jinja filter registration like `app.jinja_env.filters['currency'] = ...`. If absent, add:

```python
def _currency(value):
    if abs(value) >= 1_000_000:
        return f'£{value/1_000_000:.1f}m'
    if abs(value) >= 1_000:
        return f'£{int(value/1000)}k'
    return f'£{int(value)}'

app.jinja_env.filters['currency'] = _currency
```

- [ ] **Step 4: Start the server and play through to turn screen**

```
cd ui_web && python app.py
```

Navigate to http://localhost:5050, start a 40-turn game. On the turn screen confirm:

- ANALYTICS panel is visible below the main content
- All 3 actor columns appear with correct name colours (green/yellow/red)
- UNREALISED and AVG CAP GR are green/red based on sign
- EPC RISK shows "None" (green) or `n · £Xk` (red) correctly
- All other rows show neutral white values
- No 500 errors in terminal

- [ ] **Step 5: Commit**

```bash
git add ui_web/templates/turn.html
git commit -m "feat: add analytics dashboard panel to turn screen"
```

---

## Task 5: Final integration check

- [ ] **Step 1: Run full test suite**

```
python -m pytest tests/ -v 2>&1 | tail -40
```

Expected: all tests pass including the new `tests/test_analytics.py`.

- [ ] **Step 2: Final commit if any loose files**

```bash
git status
git add -A
git commit -m "feat: analytics dashboard complete"
```
