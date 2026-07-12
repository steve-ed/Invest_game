# Phase 1: Quarterly Turns + Regional Price Variation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the game from 6-month semi-annual turns to 3-month quarterly turns (doubling turn counts) and replace static regional growth factors with era-aware regional multipliers derived from real UK HPI divergence patterns.

**Architecture:** `uk_macro_history.py` gains a quarterly dataset built by linear interpolation. A new `data/uk_regional_hpi.py` provides `get_regional_multiplier(year, region)`. `app.py` switches its tick engine to use quarterly data — changing period multipliers from ×6 to ×3, updating `FIX_DURATIONS`, `SCENARIO_ARCS`, and the `/start` route. A regional heatmap panel is added to `turn.html`.

**Tech Stack:** Python 3, Flask, pytest, Jinja2

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `data/uk_macro_history.py` | Modify | Add `UK_MACRO_QUARTERLY`, `get_quarterly_slice()`, `get_quarterly_start_limits()` |
| `data/uk_regional_hpi.py` | Create | Era-aware regional growth multipliers |
| `ui_web/app.py` | Modify | Quarterly tick engine, updated arcs/durations, regional multiplier usage, `/start` route |
| `ui_web/templates/opening.html` | Modify | Update turn-count labels and form values (20→40, 40→80) |
| `ui_web/templates/turn.html` | Modify | Add regional heatmap panel |
| `tests/test_quarterly_macro.py` | Create | Tests for quarterly data and slice functions |
| `tests/test_regional_hpi.py` | Create | Tests for `get_regional_multiplier()` |
| `tests/test_advance_tick_quarterly.py` | Create | Tests for quarterly period multipliers in `advance_tick()` |

---

## Task 1: Quarterly interpolation in `uk_macro_history.py`

**Files:**
- Modify: `data/uk_macro_history.py`
- Create: `tests/test_quarterly_macro.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_quarterly_macro.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
import uk_macro_history as hist


def test_quarterly_has_roughly_double_entries():
    # 82 semi-annual → ~163 quarterly (last entry has no midpoint after it)
    assert len(hist.UK_MACRO_QUARTERLY) == len(hist.UK_MACRO) * 2 - 1


def test_quarterly_starts_at_same_year():
    assert hist.UK_MACRO_QUARTERLY[0][0] == hist.UK_MACRO[0][0]


def test_quarterly_first_entry_matches_semi_annual():
    q = hist.UK_MACRO_QUARTERLY[0]
    s = hist.UK_MACRO[0]
    assert q[2] == s[2]   # price_index
    assert q[3] == s[3]   # rate


def test_quarterly_interpolated_entry_is_midpoint():
    s0 = hist.UK_MACRO[0]
    s1 = hist.UK_MACRO[1]
    mid = hist.UK_MACRO_QUARTERLY[1]
    expected_pi = round((s0[2] + s1[2]) / 2, 1)
    assert abs(mid[2] - expected_pi) < 0.01


def test_get_quarterly_slice_returns_correct_count():
    slc = hist.get_quarterly_slice(1990, 1, 40)
    assert len(slc) == 40


def test_get_quarterly_slice_raises_on_missing_start():
    try:
        hist.get_quarterly_slice(1800, 1, 5)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_get_quarterly_start_limits_short_game():
    min_y, max_y = hist.get_quarterly_start_limits(40)
    assert min_y == hist.UK_MACRO_QUARTERLY[0][0]
    assert max_y >= min_y


def test_get_quarterly_start_limits_long_game():
    min_y, max_y = hist.get_quarterly_start_limits(80)
    assert max_y < 2024  # must leave 80 entries after start
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd prof_game
python -m pytest tests/test_quarterly_macro.py -v
```

Expected: all fail with `AttributeError: module 'uk_macro_history' has no attribute 'UK_MACRO_QUARTERLY'`

- [ ] **Step 3: Implement quarterly interpolation**

Add to the bottom of `data/uk_macro_history.py` (after `ERA_LABELS` block, before `get_era_label`):

```python
def _build_quarterly():
    """Interpolate UK_MACRO semi-annual data into quarterly entries."""
    result = []
    for i, entry in enumerate(UK_MACRO):
        year, half, pi, rate, rent, cpi = entry
        quarter = 1 if half == 1 else 3
        result.append((year, quarter, pi, rate, rent, cpi))
        if i + 1 < len(UK_MACRO):
            ny, nh, npi, nrate, nrent, ncpi = UK_MACRO[i + 1]
            result.append((
                year,
                quarter + 1,
                round((pi + npi) / 2, 1),
                round((rate + nrate) / 2, 2),
                round((rent + nrent) / 2, 1),
                round((cpi + ncpi) / 2, 1),
            ))
    return result


UK_MACRO_QUARTERLY = _build_quarterly()


def get_quarterly_start_limits(total_quarterly_ticks):
    """Return (min_year, max_year) for quarterly game of given length."""
    max_start_idx = len(UK_MACRO_QUARTERLY) - total_quarterly_ticks - 1
    if max_start_idx < 0:
        raise ValueError(
            f"Not enough quarterly data for {total_quarterly_ticks} ticks "
            f"(have {len(UK_MACRO_QUARTERLY)})"
        )
    return UK_MACRO_QUARTERLY[0][0], UK_MACRO_QUARTERLY[max_start_idx][0]


def get_quarterly_slice(start_year, start_quarter, count):
    """Return `count` consecutive quarterly entries from (start_year, start_quarter)."""
    idx = next(
        (i for i, e in enumerate(UK_MACRO_QUARTERLY)
         if e[0] == start_year and e[1] == start_quarter),
        None
    )
    if idx is None:
        raise ValueError(f"No quarterly data for {start_year} Q{start_quarter}")
    if idx + count > len(UK_MACRO_QUARTERLY):
        raise ValueError(
            f"Not enough quarterly data: need {count} from index {idx}, "
            f"have {len(UK_MACRO_QUARTERLY)}"
        )
    return UK_MACRO_QUARTERLY[idx:idx + count]
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_quarterly_macro.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/uk_macro_history.py tests/test_quarterly_macro.py
git commit -m "feat: add quarterly macro interpolation and slice functions"
```

---

## Task 2: Regional HPI multipliers in `data/uk_regional_hpi.py`

**Files:**
- Create: `data/uk_regional_hpi.py`
- Create: `tests/test_regional_hpi.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_regional_hpi.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
from uk_regional_hpi import get_regional_multiplier


def test_london_outperforms_national_in_late_nineties_boom():
    m = get_regional_multiplier(1999, 'London')
    assert m > 1.2, f"Expected London > 1.2 in 1999 boom, got {m}"


def test_north_underperforms_in_boom():
    m = get_regional_multiplier(1999, 'North')
    assert m < 1.0, f"Expected North < 1.0 in 1999, got {m}"


def test_london_underperforms_post_brexit():
    m = get_regional_multiplier(2019, 'London')
    assert m < 1.0, f"Expected London < 1.0 post-Brexit (2019), got {m}"


def test_midlands_tracks_national_broadly():
    m = get_regional_multiplier(2005, 'Midlands')
    assert 0.7 <= m <= 1.3, f"Midlands should be near national, got {m}"


def test_unknown_region_returns_one():
    m = get_regional_multiplier(2000, 'Atlantis')
    assert m == 1.0


def test_all_known_regions_have_multipliers():
    regions = ['London', 'South', 'East', 'West', 'Midlands', 'North', 'Scotland', 'Wales']
    for r in regions:
        m = get_regional_multiplier(2000, r)
        assert 0.3 <= m <= 3.0, f"Multiplier for {r} out of range: {m}"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_regional_hpi.py -v
```

Expected: all fail with `ModuleNotFoundError: No module named 'uk_regional_hpi'`

- [ ] **Step 3: Create `data/uk_regional_hpi.py`**

```python
# UK Regional HPI Multipliers
#
# get_regional_multiplier(year, region) returns a multiplier applied to the
# national growth rate for that region in that year.
# Derived from approximate UK regional HPI divergence patterns.

_BASE = {
    'London':   1.40,
    'South':    1.20,
    'East':     1.10,
    'West':     1.00,
    'Midlands': 0.90,
    'North':    0.80,
    'Scotland': 0.85,
    'Wales':    0.75,
}

# (start_year, end_year_inclusive, {region: multiplier})
_ERA_OVERRIDES = [
    # London/South boom and bust 1987-1993
    (1987, 1989, {'London': 1.80, 'South': 1.50, 'North': 0.65, 'Wales': 0.60}),
    (1990, 1995, {'London': 1.60, 'South': 1.40, 'North': 0.70, 'Wales': 0.65}),
    # Mid-nineties — London surges ahead
    (1996, 2000, {'London': 1.80, 'South': 1.50, 'North': 0.75}),
    # Pre-GFC London/South outperformance
    (2001, 2007, {'London': 1.60, 'South': 1.40, 'East': 1.20}),
    # GFC: convergence — London falls harder
    (2008, 2012, {'London': 0.90, 'South': 0.95, 'North': 1.05, 'Midlands': 1.00}),
    # Post-GFC London surge (Help to Buy era)
    (2013, 2016, {'London': 2.00, 'South': 1.60, 'East': 1.30}),
    # Post-Brexit: London cools, Midlands/North catch up
    (2017, 2020, {'London': 0.70, 'South': 0.80, 'North': 1.10, 'Midlands': 1.15, 'Wales': 1.10}),
    # Rate shock 2022-2024: London most exposed (high debt/value)
    (2021, 2024, {'London': 0.75, 'South': 0.85, 'North': 1.05, 'Midlands': 1.10}),
]


def get_regional_multiplier(year, region):
    """Return growth multiplier for region in year relative to national."""
    for start, end, overrides in _ERA_OVERRIDES:
        if start <= year <= end and region in overrides:
            return overrides[region]
    return _BASE.get(region, 1.0)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_regional_hpi.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/uk_regional_hpi.py tests/test_regional_hpi.py
git commit -m "feat: add era-aware regional HPI multipliers"
```

---

## Task 3: Update `advance_tick()` period multipliers

**Files:**
- Modify: `ui_web/app.py` (lines 589–626)
- Create: `tests/test_advance_tick_quarterly.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_advance_tick_quarterly.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ui_web'))
import app as web_app


def _make_gs(total_ticks=40):
    return web_app.init_game_state(total_ticks=total_ticks)


def test_rent_income_collected_for_3_months():
    gs = _make_gs()
    player = gs['player']
    monthly_rent = sum(p['rent'] for p in player['portfolio'])
    cash_before = player['cash']
    mortgages_before = sum(m['monthly_payment'] for m in player.get('mortgages', []))
    web_app.advance_tick(gs)
    # Net cash change from rent - mortgage (3 months each)
    expected_net = monthly_rent * 3 - mortgages_before * 3
    actual_net = player['cash'] - cash_before
    # Allow ±500 for rounding in property values
    assert abs(actual_net - expected_net) < 500, (
        f"Expected net ~{expected_net}, got {actual_net}"
    )


def test_rent_income_not_collected_for_6_months():
    gs = _make_gs()
    player = gs['player']
    monthly_rent = sum(p['rent'] for p in player['portfolio'])
    cash_before = player['cash']
    mortgages_before = sum(m['monthly_payment'] for m in player.get('mortgages', []))
    web_app.advance_tick(gs)
    six_month_net = monthly_rent * 6 - mortgages_before * 6
    actual_net = player['cash'] - cash_before
    # Should NOT match 6-month figure
    assert abs(actual_net - six_month_net) > 100, (
        "Cash change matched 6-month calculation — period multiplier not updated"
    )
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_advance_tick_quarterly.py -v
```

Expected: `test_rent_income_not_collected_for_6_months` PASSES (confirming current ×6 behaviour), `test_rent_income_collected_for_3_months` FAILS.

- [ ] **Step 3: Update period multipliers in `advance_tick()`**

In `ui_web/app.py`, find the `advance_tick()` function and make these changes:

Change line ~590 (rent income — 6 months → 3 months):
```python
# OLD
    ) * 6
# NEW
    ) * 3
```

Change line ~599 (mortgage payments — 6 months → 3 months):
```python
# OLD
        player['cash'] -= mortgage['monthly_payment'] * 6
# NEW
        player['cash'] -= mortgage['monthly_payment'] * 3
```

Change line ~620 (AI income — semi-annual → quarterly):
```python
# OLD
        ai_rent = int(ai['portfolio_value'] * _AI_YIELDS.get(ai['name'], 0.050) / 2)
# NEW
        ai_rent = int(ai['portfolio_value'] * _AI_YIELDS.get(ai['name'], 0.050) / 4)
```

Change line ~626 (AI debt service — 6 months → 3 months):
```python
# OLD
            ai['cash'] -= int(total_debt * gs['macro']['rate'] / 100 / 12 * 6)
# NEW
            ai['cash'] -= int(total_debt * gs['macro']['rate'] / 100 / 12 * 3)
```

Rename the variable `biannual_growth` to `quarterly_growth` throughout `advance_tick()` for clarity (3 occurrences — line ~567, ~604, ~606):
```python
# OLD
    biannual_growth = (raw_price_next - raw_price_now) / raw_price_now if raw_price_now else 0.0
# NEW
    quarterly_growth = (raw_price_next - raw_price_now) / raw_price_now if raw_price_now else 0.0
```

Update all uses of `biannual_growth` to `quarterly_growth` in `advance_tick()`.

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_advance_tick_quarterly.py -v
```

Expected: both tests PASS

- [ ] **Step 5: Run full test suite to catch regressions**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Fix any failures before continuing.

- [ ] **Step 6: Commit**

```bash
git add ui_web/app.py tests/test_advance_tick_quarterly.py
git commit -m "feat: update advance_tick period multipliers to quarterly (×3)"
```

---

## Task 4: Update `init_game_state()` and `/start` route for quarterly turns

**Files:**
- Modify: `ui_web/app.py` (init_game_state, /start route, _build_end_state, SCENARIO_ARCS, FIX_DURATIONS)

- [ ] **Step 1: Write failing test**

Add to `tests/test_advance_tick_quarterly.py`:

```python
def test_init_game_state_short_has_40_ticks():
    gs = _make_gs(total_ticks=40)
    assert gs['total_ticks'] == 40
    assert len(gs['macro_slice']) >= 40


def test_init_game_state_long_has_80_ticks():
    gs = _make_gs(total_ticks=80)
    assert gs['total_ticks'] == 80
    assert len(gs['macro_slice']) >= 80
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_advance_tick_quarterly.py::test_init_game_state_long_has_80_ticks -v
```

Expected: FAIL — `get_start_limits` doesn't have enough semi-annual data for 80 ticks.

- [ ] **Step 3: Update `init_game_state()` to use quarterly slices**

In `ui_web/app.py`, update the import at the top to include the quarterly functions:

The import is already `import uk_macro_history as hist` — no change needed.

In `init_game_state()`, replace the semi-annual slice logic:

```python
# OLD
    min_year, max_year = hist.get_start_limits(total_ticks)
    start_year = random.randint(min_year, max_year)
    start_half = random.choice([1, 2])
    while True:
        try:
            macro_slice = hist.get_slice(start_year, start_half, total_ticks)
            break
        except ValueError:
            start_half = 1
            start_year -= 1

# NEW
    min_year, max_year = hist.get_quarterly_start_limits(total_ticks)
    start_year = random.randint(min_year, max_year)
    start_quarter = random.choice([1, 2, 3, 4])
    while True:
        try:
            macro_slice = hist.get_quarterly_slice(start_year, start_quarter, total_ticks)
            break
        except ValueError:
            start_quarter = 1
            start_year -= 1
```

Also update the gs dict to use `real_start_quarter` instead of `real_start_half`:

```python
# OLD
        'real_start_year': start_year,
        'real_start_half': start_half,
# NEW
        'real_start_year': start_year,
        'real_start_half': start_quarter,   # kept as 'real_start_half' key for template compatibility
```

- [ ] **Step 4: Update `FIX_DURATIONS` for quarterly ticks**

```python
# OLD
FIX_DURATIONS  = {'fixed_2yr': 4, 'fixed_5yr': 10}   # ticks (semi-annual periods)
# NEW
FIX_DURATIONS  = {'fixed_2yr': 8, 'fixed_5yr': 20}   # ticks (quarterly periods)
```

- [ ] **Step 5: Update `SCENARIO_ARCS` for new turn counts**

Replace the `SCENARIO_ARC_20`, `SCENARIO_ARC_40`, and `SCENARIO_ARCS` definitions:

```python
SCENARIO_ARC_40 = [
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
```

- [ ] **Step 6: Update `/start` route to accept 40/80**

```python
# OLD
        total_ticks = int(request.form.get('total_ticks', 20))
    ...
    if total_ticks not in (20, 40):
        total_ticks = 20
# NEW
        total_ticks = int(request.form.get('total_ticks', 40))
    ...
    if total_ticks not in (40, 80):
        total_ticks = 40
```

- [ ] **Step 7: Update `_build_end_state()` to use quarterly start limits**

Find line ~719:
```python
# OLD
    min_year, max_year = hist.get_start_limits(gs['total_ticks'])
# NEW
    min_year, max_year = hist.get_quarterly_start_limits(gs['total_ticks'])
```

- [ ] **Step 8: Run tests to confirm they pass**

```
python -m pytest tests/test_advance_tick_quarterly.py -v
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Fix any failures before continuing.

- [ ] **Step 9: Commit**

```bash
git add ui_web/app.py
git commit -m "feat: switch game to quarterly turns (40/80 ticks, quarterly macro slice)"
```

---

## Task 5: Use regional multipliers from `uk_regional_hpi.py` in `advance_tick()`

**Files:**
- Modify: `ui_web/app.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_advance_tick_quarterly.py`:

```python
def test_london_property_grows_faster_than_north_in_boom_era():
    import copy
    # Find a boom era start: pick 1999 Q1 (known London outperformance)
    import uk_macro_history as hist_mod
    try:
        slc = hist_mod.get_quarterly_slice(1999, 1, 41)
    except ValueError:
        return  # skip if data not available at this start point

    gs = web_app.init_game_state(total_ticks=40)
    # Manually inject a London and a North property at same value
    london_prop = {'id': 'TEST-L', 'region': 'London', 'value': 200000, 'rent': 1000, 'epc_compliant': True}
    north_prop  = {'id': 'TEST-N', 'region': 'North',  'value': 200000, 'rent': 1000, 'epc_compliant': True}
    gs['player']['portfolio'].extend([london_prop, north_prop])
    # Override macro_slice to a boom era
    gs['macro_slice'] = slc
    gs['price_scale'] = 100.0 / slc[0][2]
    gs['real_start_year'] = 1999

    web_app.advance_tick(gs)

    london_val = next(p['value'] for p in gs['player']['portfolio'] if p['id'] == 'TEST-L')
    north_val  = next(p['value'] for p in gs['player']['portfolio'] if p['id'] == 'TEST-N')
    assert london_val > north_val, (
        f"London ({london_val}) should exceed North ({north_val}) in 1999 boom"
    )
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_advance_tick_quarterly.py::test_london_property_grows_faster_than_north_in_boom_era -v
```

Expected: FAIL if London and North currently get the same multiplier path, or PASS if REGION_PROFILES already handles this. If it already passes, skip to Task 6.

- [ ] **Step 3: Import `uk_regional_hpi` in `app.py`**

Add near the top of `ui_web/app.py` alongside other data imports:

```python
import uk_regional_hpi as regional_hpi
```

- [ ] **Step 4: Replace static `growth_factor` with `get_regional_multiplier()` in `advance_tick()`**

In `advance_tick()`, find the player portfolio update block (~line 603):

```python
# OLD
    for p in player['portfolio']:
        gf = REGION_PROFILES.get(p.get('region', 'West'), {}).get('growth_factor', 1.0)
        rg = quarterly_growth * gf
# NEW
    year = current_real_year(gs)
    for p in player['portfolio']:
        gf = regional_hpi.get_regional_multiplier(year, p.get('region', 'West'))
        rg = quarterly_growth * gf
```

Do the same for the market update block (~line 612):

```python
# OLD
    for p in gs['market']:
        gf = REGION_PROFILES.get(p.get('region', 'West'), {}).get('growth_factor', 1.0)
        rg = quarterly_growth * gf
# NEW
    for p in gs['market']:
        gf = regional_hpi.get_regional_multiplier(year, p.get('region', 'West'))
        rg = quarterly_growth * gf
```

Note: `year` is already computed above (from `current_real_year(gs)`) — no duplicate call needed.

- [ ] **Step 5: Run tests**

```
python -m pytest tests/test_advance_tick_quarterly.py -v
python -m pytest tests/test_regional_hpi.py -v
python -m pytest tests/ --tb=short 2>&1 | tail -20
```

Fix any failures before continuing.

- [ ] **Step 6: Commit**

```bash
git add ui_web/app.py
git commit -m "feat: use era-aware regional HPI multipliers in advance_tick"
```

---

## Task 6: Update `opening.html` turn-count labels

**Files:**
- Modify: `ui_web/templates/opening.html`

- [ ] **Step 1: Update turn-count form values in `ui_web/templates/opening.html`**

The mode selector is at line ~126–165. Make these changes:

```html
<!-- OLD -->
<div ... id="label-20" onclick="selectMode(20)">
  <input type="radio" name="total_ticks" value="20" checked style="display:none;" id="mode-20">
  <div ...>20 TURNS</div>
  ...
<div ... id="label-40" onclick="selectMode(40)">
  <input type="radio" name="total_ticks" value="40" style="display:none;" id="mode-40">
  <div ...>40 TURNS</div>
  <div class="muted" ...>20 years &nbsp;&middot;&nbsp; 2 macro cycles</div>

<!-- NEW — change values, IDs, labels, and JS -->
<div ... id="label-40" onclick="selectMode(40)">
  <input type="radio" name="total_ticks" value="40" checked style="display:none;" id="mode-40">
  <div ...>40 TURNS</div>
  <div class="muted" ...>10 years &nbsp;&middot;&nbsp; quarterly decisions</div>
<div ... id="label-80" onclick="selectMode(80)">
  <input type="radio" name="total_ticks" value="80" style="display:none;" id="mode-80">
  <div ...>80 TURNS</div>
  <div class="muted" ...>20 years &nbsp;&middot;&nbsp; 2 macro cycles</div>
```

Update the JS function at line ~158:
```javascript
// OLD
  document.getElementById('mode-20').checked = (n === 20);
  document.getElementById('mode-40').checked = (n === 40);
  document.getElementById('label-20').style.borderColor = (n === 20) ? 'var(--accent)' : 'var(--border)';
  document.getElementById('label-40').style.borderColor = (n === 40) ? 'var(--accent)' : 'var(--border)';
  ...
  selectMode(20);

// NEW
  document.getElementById('mode-40').checked = (n === 40);
  document.getElementById('mode-80').checked = (n === 80);
  document.getElementById('label-40').style.borderColor = (n === 40) ? 'var(--accent)' : 'var(--border)';
  document.getElementById('label-80').style.borderColor = (n === 80) ? 'var(--accent)' : 'var(--border)';
  ...
  selectMode(40);
```

- [ ] **Step 2: Smoke-test manually**

Start the Flask app:
```bash
cd ui_web && python app.py
```

Open http://localhost:5050. Confirm:
- Opening screen shows "40 turns" and "80 turns"
- Selecting Short and starting a game shows "Turn 1 of 40" (not "Turn 1 of 20")
- Game advances correctly through turns

- [ ] **Step 3: Commit**

```bash
git add ui_web/templates/opening.html
git commit -m "feat: update opening screen for quarterly turn counts (40/80)"
```

---

## Task 7: Add regional heatmap to `turn.html`

**Files:**
- Modify: `ui_web/app.py` (turn route — add `regional_growths` to template context)
- Modify: `ui_web/templates/turn.html`

- [ ] **Step 1: Add regional growth data to the turn route**

In `ui_web/app.py`, find the `/turn` route handler (~line 838). Add regional growth calculation before the `render_template` call:

```python
# Compute regional growth vs national for heatmap
year = current_real_year(GAME_STATE)
nat_growth = (
    (GAME_STATE['macro']['price_index'] - GAME_STATE['macro']['prev']['price_index'])
    / GAME_STATE['macro']['prev']['price_index'] * 100
    if GAME_STATE['macro']['prev']['price_index'] else 0.0
)
regional_growths = {
    region: round(nat_growth * regional_hpi.get_regional_multiplier(year, region), 2)
    for region in ['London', 'South', 'East', 'West', 'Midlands', 'North', 'Scotland', 'Wales']
}
```

Pass `regional_growths=regional_growths` and `national_growth=round(nat_growth, 2)` to `render_template`.

- [ ] **Step 2: Add heatmap panel to `turn.html`**

Add a new panel section in the turn dashboard (after the macro sidebar or as a sidebar addition). Insert:

```html
<!-- Regional Growth Heatmap -->
<div class="panel">
  <h4>Regional Growth This Quarter</h4>
  <table class="heatmap-table">
    <tr>
      <th>Region</th>
      <th>Growth %</th>
      <th>vs National</th>
    </tr>
    {% for region, growth in regional_growths.items() | sort(attribute='1', reverse=True) %}
    {% set diff = growth - national_growth %}
    <tr class="{% if diff > 0.3 %}heat-hot{% elif diff < -0.3 %}heat-cold{% else %}heat-neutral{% endif %}">
      <td>{{ region }}</td>
      <td>{{ growth }}%</td>
      <td>{% if diff > 0 %}+{% endif %}{{ diff | round(2) }}%</td>
    </tr>
    {% endfor %}
  </table>
</div>
```

Add CSS classes to the template's `<style>` block (or base.html if styles are centralised):

```css
.heatmap-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.heatmap-table th, .heatmap-table td { padding: 3px 8px; text-align: left; }
.heat-hot  { background: rgba(220, 38, 38, 0.15); }
.heat-cold { background: rgba(37, 99, 235, 0.15); }
.heat-neutral { background: transparent; }
```

- [ ] **Step 3: Smoke-test the heatmap**

```bash
cd ui_web && python app.py
```

Start a short game at http://localhost:5050. Confirm:
- Regional heatmap panel is visible on the turn screen
- London shows red (hot) in boom eras, blue (cold) in correction eras
- North shows the inverse pattern
- "vs National" column shows + and − values

- [ ] **Step 4: Commit**

```bash
git add ui_web/app.py ui_web/templates/turn.html
git commit -m "feat: add regional growth heatmap panel to turn dashboard"
```

---

## Task 8: Final integration test

- [ ] **Step 1: Run full test suite**

```
python -m pytest tests/ -v 2>&1 | tail -40
```

Expected: all existing tests pass; new tests for quarterly macro, regional HPI, and advance_tick pass.

- [ ] **Step 2: Play a short game end-to-end**

Start the server and play a complete short game (40 turns):
- Confirm turn counter shows "Turn N of 40"
- Confirm fixed rate mortgages expire at the right time (2-year fix = 8 turns, 5-year = 20 turns)
- Confirm the era reveal on the end screen shows a valid historical period
- Confirm regional heatmap updates each turn

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Phase 1 complete — quarterly turns and regional HPI variation"
```
