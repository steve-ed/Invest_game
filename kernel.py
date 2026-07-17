import sys
import io
import json
import random
import os
import threading
import time

from state import SimulationState, Property, ActorState, MacroState, MacroSnapshot
from shocks import detect_events
from scenarios import label_from_deltas
from actors import ActorManager
from ai import AIController
from narrative.branching import BranchingEngine
from narrative.scenario_events import ScenarioEventEngine
from player.choices import PlayerChoiceEngine, ACTION_PATH as PLAYER_ACTION_PATH
from property_model import PropertyModel
from scoring import ScoringEngine
from void_maintenance import VoidMaintenanceEngine, void_risk_pct, maintenance_risk_label, expected_maintenance_reserve
from ui.dashboard import show_opening, show_end
from data.uk_macro_history import get_slice, get_start_limits, get_era_label, get_preamble_slice

TURN_STATE_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "turn_state.json")
READY_PATH       = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
EPC_GRACE_TICKS  = 4
MORTGAGE_SPREAD  = 0.018  # lender margin above BoE base rate
_VOID_BY_ARCHETYPE = {"btl": 0, "new_build": 0, "hmo": 1, "value_add": 1, "short_let": 1}

_MARKET_NATIONAL_BASE = 165_000
_MARKET_REGION_PROFILES = {
    "London":   {"price_level": 2.50, "annual_yield": 0.035, "epc_bands": [2, 3],    "hpi_factor": 1.35},
    "South":    {"price_level": 1.50, "annual_yield": 0.040, "epc_bands": [3, 4],    "hpi_factor": 1.15},
    "East":     {"price_level": 1.20, "annual_yield": 0.045, "epc_bands": [3, 4],    "hpi_factor": 1.10},
    "West":     {"price_level": 1.00, "annual_yield": 0.048, "epc_bands": [4, 5],    "hpi_factor": 0.95},
    "Midlands": {"price_level": 0.85, "annual_yield": 0.055, "epc_bands": [4, 5],    "hpi_factor": 0.90},
    "North":    {"price_level": 0.75, "annual_yield": 0.060, "epc_bands": [5, 6],    "hpi_factor": 0.85},
    "Scotland": {"price_level": 0.80, "annual_yield": 0.055, "epc_bands": [4, 5],    "hpi_factor": 0.88},
    "Wales":    {"price_level": 0.70, "annual_yield": 0.065, "epc_bands": [5, 6, 7], "hpi_factor": 0.80},
}
_MARKET_REGIONS       = list(_MARKET_REGION_PROFILES.keys())
_MARKET_MIN_AVAILABLE = 4
_MARKET_TARGET        = 6

_CITY_TO_REGION = {
    "London": "London", "Oxford": "South", "Brighton": "South",
    "Bristol": "South", "Cambridge": "East", "Cardiff": "Wales",
    "Sheffield": "North", "Leeds": "North", "Manchester": "North",
    "Liverpool": "North", "Newcastle": "North", "Sunderland": "North",
    "Leicester": "Midlands", "Birmingham": "Midlands", "Nottingham": "Midlands",
    "Scotland": "Scotland",
}


def _hpi_for_city(city: str) -> float:
    for key, region in _CITY_TO_REGION.items():
        if key in city:
            return _MARKET_REGION_PROFILES[region]["hpi_factor"]
    return 1.0


def _select_advice(state, player_actor, available, ai_controller,
                   rank, score_gap, ticks_remaining, opp_strategies):
    """Choose which strategy to recommend based on competitive position."""
    if not player_actor:
        return "hold", None, 0.0, "balanced"

    end_game  = ticks_remaining <= 4
    desperate = ticks_remaining <= 4 and score_gap > 150_000 and rank > 1

    if rank == 1:
        strategy = "yield" if end_game else "balanced"
    elif desperate:
        strategy = "leverage"
    elif "capital" in opp_strategies and rank > 1:
        # Can't out-appreciate a capital strategy — out-yield instead
        strategy = "yield"
    else:
        strategy = "balanced"

    method = getattr(ai_controller, f"_decide_{strategy}")

    # Get strategic advice without the upgrade gate so that one un-upgraded property
    # doesn't permanently block buy/refi/hold recommendations.
    _orig_check = ai_controller._check_upgrade
    ai_controller._check_upgrade = lambda state, actor: None
    try:
        action, prop, ltv = method(state, player_actor, available)
    finally:
        ai_controller._check_upgrade = _orig_check

    # Only surface upgrade in advice when the EPC mandate is active or approaching,
    # and no strategic move is available.
    if action == "hold" and state.epc_mandate_announced:
        upg = _orig_check(state, player_actor)
        if upg:
            return upg[0], upg[1], upg[2], strategy

    return action, prop, ltv, strategy


def _eval_comment(player_action, adv_action, adv_prop, rate, scenario,
                  rank, score_gap, adv_strategy, ticks_remaining):
    """Position-aware comment explaining recommended action."""
    pa_verb = player_action.split()[0] if player_action else "hold"
    pa_prop = player_action.split()[1] if " " in (player_action or "") else None

    # Position label
    if rank == 1:
        pos = "leading"
    else:
        pos = f"£{score_gap:,.0f} behind"

    agreed = pa_verb == adv_action and (adv_action != "buy" or pa_prop == adv_prop)
    if agreed:
        if rank == 1 and adv_strategy == "yield":
            return f"Good — protecting lead with conservative play ({ticks_remaining} turns left)."
        if rank > 1 and adv_strategy == "leverage":
            return f"Agreed — aggressive buying needed to close £{score_gap:,.0f} gap."
        return "Agreed."

    if pa_verb == "hold" and adv_action == "buy":
        base = f"{adv_prop} offered yield at {rate:.1f}%." if adv_prop else "A buying opportunity was available."
        if rank > 1 and score_gap > 100_000:
            base += f" Buying accelerates return vs being {pos}."
        return base

    if pa_verb == "buy" and adv_action == "hold":
        if adv_strategy == "yield" and rank == 1:
            return f"Hold preferred — protect lead at {rate:.1f}%, avoid rate exposure."
        return f"Hold preferred at {rate:.1f}% — rate-risk exposure rises."

    if pa_verb == "buy" and adv_action == "buy" and pa_prop != adv_prop:
        return f"Bought, but {adv_prop} had better relative yield."

    if pa_verb == "sell" and adv_action == "hold":
        return "Early sale — may have crystallised unnecessary loss."

    if pa_verb == "hold" and adv_action == "sell":
        return "Sell preferred — holding increases rate-stress exposure."

    if pa_verb == "upgrade" and adv_action != "upgrade":
        if rank > 1 and adv_strategy == "leverage":
            return f"Upgrade can wait — buying is the priority to close {pos}."
        return "Upgrade was early; worthwhile if EPC mandate is imminent."

    if pa_verb != "upgrade" and adv_action == "upgrade":
        return f"Upgrade {adv_prop} to avoid EPC scoring penalty and void risk."

    if pa_verb == "hold" and adv_action == "refi":
        return f"Refi {adv_prop} to extract equity and stay competitive."

    return f"Advises '{adv_action}' ({adv_strategy} strategy, {pos})."


def _default_properties():
    props = [
        Property(id="p01", region="London Kensington",   base_value=500000.0, current_value=500000.0, rent=2500.0, archetype="btl",       epc_band=3, age=60,  bedrooms=3),
        Property(id="p02", region="Oxford",              base_value=230000.0, current_value=230000.0, rent=1150.0, archetype="btl",       epc_band=4, age=50,  bedrooms=3),
        Property(id="p03", region="Brighton",            base_value=220000.0, current_value=220000.0, rent=1100.0, archetype="btl",       epc_band=4, age=45,  bedrooms=2),
        Property(id="p04", region="Sheffield",           base_value=130000.0, current_value=130000.0, rent=650.0,  archetype="value_add", epc_band=5, age=80,  bedrooms=3),
        Property(id="p05", region="Leicester",           base_value=140000.0, current_value=140000.0, rent=700.0,  archetype="value_add", epc_band=5, age=75,  bedrooms=3),
        Property(id="p06", region="Bristol",             base_value=260000.0, current_value=260000.0, rent=1300.0, archetype="btl",       epc_band=3, age=35,  bedrooms=3),
        Property(id="p07", region="Cambridge",           base_value=250000.0, current_value=250000.0, rent=1250.0, archetype="btl",       epc_band=3, age=30,  bedrooms=2),
        Property(id="p08", region="Birmingham",          base_value=200000.0, current_value=200000.0, rent=1000.0, archetype="value_add", epc_band=5, age=70,  bedrooms=3),
        Property(id="p09", region="Manchester",          base_value=240000.0, current_value=240000.0, rent=1200.0, archetype="btl",       epc_band=4, age=40,  bedrooms=3),
        Property(id="p10", region="Leeds",               base_value=170000.0, current_value=170000.0, rent=850.0,  archetype="value_add", epc_band=5, age=65,  bedrooms=3),
        Property(id="p11", region="Nottingham",          base_value=240000.0, current_value=240000.0, rent=1800.0, archetype="hmo",       epc_band=5, age=70,  bedrooms=5),
        Property(id="p12", region="Liverpool",           base_value=220000.0, current_value=220000.0, rent=1950.0, archetype="hmo",       epc_band=5, age=85,  bedrooms=6),
        Property(id="p13", region="Cardiff",             base_value=160000.0, current_value=160000.0, rent=800.0,  archetype="btl",       epc_band=4, age=55,  bedrooms=3),
        Property(id="p14", region="Newcastle",           base_value=120000.0, current_value=120000.0, rent=600.0,  archetype="value_add", epc_band=5, age=90,  bedrooms=2),
        Property(id="p15", region="Sunderland",          base_value=90000.0,  current_value=90000.0,  rent=540.0,  archetype="value_add", epc_band=5, age=95,  bedrooms=2),
        Property(id="m1",  region="London Shoreditch",   base_value=420000.0, current_value=420000.0, rent=2800.0, archetype="short_let", epc_band=2, age=15,  bedrooms=1),
        Property(id="m2",  region="Bristol Harbourside", base_value=230000.0, current_value=230000.0, rent=1035.0, archetype="new_build", epc_band=1, age=2,   bedrooms=2),
        Property(id="m3",  region="Leeds City Centre",   base_value=230000.0, current_value=230000.0, rent=1950.0, archetype="hmo",       epc_band=4, age=30,  bedrooms=5),
        Property(id="m4",  region="Sunderland Dockside", base_value=80000.0,  current_value=80000.0,  rent=560.0,  archetype="value_add", epc_band=6, age=100, bedrooms=2),
    ]
    for p in props:
        p.hpi_factor = _hpi_for_city(p.region)
        hpi_value = round(p.base_value * p.hpi_factor / 1000) * 1000
        discount = _EPC_PRICE_DISCOUNT.get(p.epc_band, 0)
        p.current_value = round(hpi_value * (1 - discount) / 1000) * 1000
        p.base_value = p.current_value
    return props


_STARTING_WEALTH = 1_500_000  # all actors start with the same total wealth (hpi-adjusted equity + cash)

_STRATEGY_PROFILES = {
    # hpi-adjusted: p04 Sheffield(N×0.85)=111k, p05 Leicester(M×0.90)=126k → equity 237k → cash 1,263k
    "yield":       {"name": "Ms Di Vidend",      "risk_appetite": 0.25, "cash": 1_263_000, "portfolio": ["p04", "p05"]},
    # hpi-adjusted: p06 Bristol(S×1.15)=299k, p07 Cambridge(E×1.10)=275k → equity 574k → cash 926k
    "capital":     {"name": "Mr Hugh Price",     "risk_appetite": 0.55, "cash":   926_000, "portfolio": ["p06", "p07"]},
    # hpi-adjusted: p08 Birmingham(M×0.90)=180k, p09 Manchester(N×0.85)=204k → equity 384k → cash 1,116k
    "value_add":   {"name": "Mr Ray Novate",     "risk_appetite": 0.65, "cash": 1_116_000, "portfolio": ["p08", "p09"]},
    # hpi-adjusted: p10 Leeds(N×0.85)=144k, p11 Nottingham(M×0.90)=216k → equity 360k → cash 1,140k
    "brrr":        {"name": "Mr Reid Furbish",   "risk_appetite": 0.70, "cash": 1_140_000, "portfolio": ["p10", "p11"]},
    # hpi-adjusted: p12 Liverpool(N×0.85)=187k, p13 Cardiff(W×0.80)=128k → equity 315k → cash 1,185k
    "leverage":    {"name": "Mr Max Lever",       "risk_appetite": 0.90, "cash": 1_185_000, "portfolio": ["p12", "p13"]},
    # hpi-adjusted: p14 Newcastle(N×0.85)=102k, p15 Sunderland(N×0.85)=76k → equity 178k → cash 1,322k
    "demographic": {"name": "Ms Demi Graphic",   "risk_appetite": 0.50, "cash": 1_322_000, "portfolio": ["p14", "p15"]},
}


def _default_actors():
    import random
    ai1_strat, ai2_strat = random.sample(list(_STRATEGY_PROFILES.keys()), 2)
    p1 = _STRATEGY_PROFILES[ai1_strat]
    p2 = _STRATEGY_PROFILES[ai2_strat]
    prop_map = {p.id: p for p in _default_properties()}
    ai_owned = set(p1["portfolio"]) | set(p2["portfolio"])
    eligible = [pid for pid in prop_map if pid.startswith("p") and pid[1:].isdigit() and pid not in ai_owned]
    player_portfolio = random.sample(eligible, 3)
    equity = sum(prop_map[pid].current_value for pid in player_portfolio)
    player_cash = min(550_000, max(100_000, _STARTING_WEALTH - equity))
    return {
        "player": ActorState(id="player", name="You", cash=player_cash, risk_appetite=0.6,
                             strategy="balanced", portfolio=player_portfolio),
        "ai1":    ActorState(id="ai1",   name=p1["name"], cash=p1["cash"],
                             risk_appetite=p1["risk_appetite"], strategy=ai1_strat,
                             portfolio=list(p1["portfolio"])),
        "ai2":    ActorState(id="ai2",   name=p2["name"], cash=p2["cash"],
                             risk_appetite=p2["risk_appetite"], strategy=ai2_strat,
                             portfolio=list(p2["portfolio"])),
    }


def _portfolio_value(actor, properties):
    prop_map = {p.id: p for p in properties}
    return sum(prop_map[pid].current_value for pid in actor.portfolio if pid in prop_map)


def _calculate_sdlt(price: float) -> float:
    """SDLT for additional residential property (3% surcharge applies to all bands)."""
    bands = [
        (125_000, 0.03),
        (125_000, 0.05),
        (675_000, 0.08),
        (575_000, 0.13),
    ]
    tax, remaining = 0.0, price
    for band_size, rate in bands:
        taxable = min(remaining, band_size)
        tax += taxable * rate
        remaining -= taxable
        if remaining <= 0:
            break
    if remaining > 0:
        tax += remaining * 0.15
    return round(tax, 2)


def _epc_upgrade_cost(epc_band: int) -> float:
    """Estimated retrofit cost to bring property to EPC C."""
    return {4: 5_000, 5: 8_000, 6: 10_000, 7: 10_000}.get(epc_band, 0.0)


# Purchase discount and matching value uplift on upgrade for poor-EPC properties.
# Poor EPC deters buyers, so market prices reflect the cost/risk of non-compliance.
_EPC_PRICE_DISCOUNT = {4: 0.05, 5: 0.08, 6: 0.12, 7: 0.15}
_EPC_VALUE_UPLIFT   = {4: 0.06, 5: 0.10, 6: 0.15, 7: 0.18}


def _select_era(turns):
    min_year, max_year = get_start_limits(turns)
    start_year = random.randint(min_year, max_year)
    start_half = random.choice([1, 2])
    return start_year, start_half


def _normalize_slice(raw_slice):
    """Normalise price_index so the first entry = 100."""
    base_hpi = raw_slice[0][2]
    return [
        (year, half, price_index / base_hpi * 100, rate, rent_growth, cpi)
        for year, half, price_index, rate, rent_growth, cpi in raw_slice
    ]


class SimulationKernel:
    def __init__(self, turns=20, mode="student", turn_delay=3, bus=None):
        self.turns = turns
        self.mode = mode
        self.turn_delay = 0  # state is written immediately; TURN_SECONDS timer handles pacing
        self._bus = bus

        start_year, start_half = _select_era(turns)
        raw_slice = get_slice(start_year, start_half, turns)
        self.historical_slice = _normalize_slice(raw_slice)
        self.era_label = get_era_label(start_year)

        # Pre-game preamble: 2 years of history before the start, normalised to same base
        raw_preamble = get_preamble_slice(start_year, start_half)
        game_base_hpi = raw_slice[0][2]
        self.preamble_macro = [
            {"label": f"{y} H{h}", "price_index": round(pi / game_base_hpi * 100, 2),
             "rate": round(r, 2), "rent_growth": round(rg, 2)}
            for y, h, pi, r, rg, _ in raw_preamble
        ]

        self.state = SimulationState()
        self.state.properties = _default_properties()
        self.state.actors = _default_actors()
        self.state.start_year = start_year
        self.state.start_half = start_half
        self.state.era_label = self.era_label

        self.actors = ActorManager()
        self.ai = AIController()
        self.branching = BranchingEngine()
        self.scenario_events = ScenarioEventEngine()
        self.player_choices = PlayerChoiceEngine(bus=bus)
        self.property_model = PropertyModel()
        self.scoring = ScoringEngine()
        self.void_maintenance = VoidMaintenanceEngine()
        self._epc_warned = {}           # property_id -> tick when mandate warning issued
        self._epc_mandate_tick = random.randint(5, 8)
        self._epc_mandate_announced = False
        self._next_market_id = 100  # ids mk100+ avoid clashing with p01-p15, m1-m4
        for actor in self.state.actors.values():
            pv = _portfolio_value(actor, self.state.properties)
            actor.initial_wealth = actor.cash + pv
        self._wealth_history = []
        self._macro_history_export = []
        self._player_eval = []
        self._axis_ranges = self._compute_axis_ranges()

    def _compute_axis_ranges(self):
        hpi   = [e[2] for e in self.historical_slice]
        rates = [e[3] for e in self.historical_slice]
        rents = [e[4] for e in self.historical_slice]

        # cumulative inflation trajectory (compounded semi-annually)
        cum_inf, cum_inf_values = 100.0, []
        for entry in self.historical_slice:
            cum_inf *= (1 + entry[5] / 100 / 2)
            cum_inf_values.append(cum_inf)

        def _pad(values, pct=0.15):
            lo, hi = min(values), max(values)
            pad = max((hi - lo) * pct, abs(hi) * 0.03, 0.1)
            return round(lo - pad, 2), round(hi + pad, 2)

        # Wealth upper bound: assume all initial wealth converted to property at
        # the lowest HPI point then sold at the highest — loosest safe upper bound.
        hpi_swing = max(hpi) / min(hpi)
        wealth_peaks = []
        for actor in self.state.actors.values():
            pv = _portfolio_value(actor, self.state.properties)
            wealth_peaks.append((actor.cash + pv) * hpi_swing)

        # Wealth lower bound: portfolio at minimum HPI, cash unchanged
        wealth_floors = []
        for actor in self.state.actors.values():
            pv = _portfolio_value(actor, self.state.properties)
            wealth_floors.append(pv * min(hpi) / 100.0)

        # yHPI axis covers both price_index and cumulative_inflation
        all_index_values = hpi + cum_inf_values

        return {
            "hpi":  list(_pad(all_index_values)),
            "rate": list(_pad(rates)),
            "rent": list(_pad(rents)),
        }

    def _apply_macro(self, entry):
        _, _, price_index, rate, rent_growth, _cpi = entry
        self.state.macro = MacroState(
            price_index=price_index,
            interest_rate=rate / 100.0,
            rent_growth=rent_growth / 100.0,
        )

    def _write_turn_state(self, current_events, is_final=False):
        actors_data = {}
        for actor_id, actor in self.state.actors.items():
            prop_map_a = {p.id: p for p in self.state.properties}
            pv = _portfolio_value(actor, self.state.properties)
            total_mortgage = sum(
                prop_map_a[pid].mortgage_balance
                for pid in actor.portfolio if pid in prop_map_a
            )
            equity = pv - total_mortgage
            actors_data[actor_id] = {
                "name": actor.name,
                "cash": round(actor.cash, 2),
                "portfolio_value": round(pv, 2),
                "total": round(actor.cash + equity, 2),
            }

        x_labels = ["Start"] + [f"{year} H{half}" for year, half, *_ in self.historical_slice]

        player = self.state.actors.get("player")
        prop_map = {p.id: p for p in self.state.properties}
        owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}

        player_portfolio = []
        total_rent = 0.0
        total_mortgage_cost = 0.0
        if player:
            for pid in player.portfolio:
                p = prop_map.get(pid)
                if p:
                    monthly_mortgage = round((p.mortgage_balance * p.mortgage_rate) / 12, 0)
                    pnl_abs = round(p.current_value - p.base_value, 0)
                    pnl_pct = round((p.current_value - p.base_value) / p.base_value * 100, 1) if p.base_value > 0 else 0.0
                    total_rent += p.rent
                    total_mortgage_cost += monthly_mortgage
                    player_portfolio.append({
                        "id": p.id, "region": p.region,
                        "value": round(p.current_value, 0),
                        "rent_monthly": round(p.rent, 0),
                        "epc_band": p.epc_band,
                        "epc_label": chr(64 + p.epc_band),
                        "mortgage": round(p.mortgage_balance, 0),
                        "fixed_ticks_remaining": p.fixed_ticks_remaining,
                        "monthly_mortgage": monthly_mortgage,
                        "archetype": p.archetype,
                        "bedrooms": p.bedrooms,
                        "pnl_abs": pnl_abs,
                        "pnl_pct": pnl_pct,
                        "gross_yield_pct": round(p.rent * 12 / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "net_yield_pct": round((p.rent * 12 - monthly_mortgage * 12) / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "ltv_pct": round(p.mortgage_balance / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "equity": round(p.current_value - p.mortgage_balance, 0),
                        "refi_headroom": round(max(0.0, p.current_value * 0.75 - p.mortgage_balance), 0) if p.fixed_ticks_remaining == 0 else 0,
                        "epc_upgrade_cost": _epc_upgrade_cost(p.epc_band),
                        "void_ticks_remaining": p.void_ticks_remaining,
                        "age": p.age,
                        "maintenance_risk": maintenance_risk_label(p),
                        "renovated": p.renovated,
                    })

        # Per-actor state for dashboard turn sequence panels
        actors_state = {}
        for a_id, actor in self.state.actors.items():
            a_rent, a_mtg, a_portfolio = 0.0, 0.0, []
            for pid in actor.portfolio:
                p = prop_map.get(pid)
                if p:
                    mm = round((p.mortgage_balance * p.mortgage_rate) / 12, 0)
                    pnl_abs = round(p.current_value - p.base_value, 0)
                    pnl_pct = round((p.current_value - p.base_value) / p.base_value * 100, 1) if p.base_value > 0 else 0.0
                    a_rent += p.rent
                    a_mtg  += mm
                    a_portfolio.append({
                        "id": p.id, "region": p.region,
                        "value": round(p.current_value, 0),
                        "rent_monthly": round(p.rent, 0),
                        "epc_band": p.epc_band, "epc_label": chr(64 + p.epc_band),
                        "mortgage": round(p.mortgage_balance, 0), "monthly_mortgage": mm,
                        "fixed_ticks_remaining": p.fixed_ticks_remaining,
                        "archetype": p.archetype, "bedrooms": p.bedrooms,
                        "pnl_abs": pnl_abs, "pnl_pct": pnl_pct,
                        "gross_yield_pct": round(p.rent * 12 / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "net_yield_pct": round((p.rent * 12 - mm * 12) / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "ltv_pct": round(p.mortgage_balance / p.current_value * 100, 1) if p.current_value > 0 else 0.0,
                        "equity": round(p.current_value - p.mortgage_balance, 0),
                        "refi_headroom": round(max(0.0, p.current_value * 0.75 - p.mortgage_balance), 0) if p.fixed_ticks_remaining == 0 else 0,
                        "epc_upgrade_cost": _epc_upgrade_cost(p.epc_band),
                    })
            a_delta = None
            if len(self._wealth_history) >= 2:
                curr_w = self._wealth_history[-1].get(a_id, 0)
                prev_w = self._wealth_history[-2].get(a_id, 0)
                d_total = round(curr_w - prev_w, 0)
                r6 = round(a_rent * 6, 0)
                m6 = round(a_mtg  * 6, 0)
                a_delta = {"total": d_total, "rent": r6, "mortgage": m6,
                           "appreciation": round(d_total - r6 + m6, 0)}
            a_pv      = sum(p["value"]    for p in a_portfolio)
            a_mtg_tot = sum(p["mortgage"] for p in a_portfolio)
            a_equity  = a_pv - a_mtg_tot
            a_unrealised = round(sum(p["pnl_abs"] for p in a_portfolio), 0)
            a_gross_yield = round(a_rent * 12 / a_pv * 100, 1) if a_pv > 0 else 0.0
            a_annual_net  = (a_rent - a_mtg) * 12
            a_roe = round(a_annual_net / a_equity * 100, 1) if a_equity > 0 else None
            _epc_thresh      = 4 if self.state.epc_mandate_announced else 6
            a_epc_risk_props = [p for p in a_portfolio if p["epc_band"] >= _epc_thresh]
            a_arch: dict[str, float] = {}
            a_beds: dict[str, int] = {}
            a_regions: dict[str, float] = {}
            for p in a_portfolio:
                a_arch[p["archetype"]] = a_arch.get(p["archetype"], 0) + p["value"]
                bed_key = f"{p['bedrooms']}bd" if p["bedrooms"] < 4 else "4+bd"
                a_beds[bed_key] = a_beds.get(bed_key, 0) + 1
                a_regions[p["region"]] = a_regions.get(p["region"], 0) + p["value"]
            a_arch_total = sum(a_arch.values()) or 1.0
            a_beds_total = sum(a_beds.values()) or 1

            # avg mortgage rate across leveraged properties
            leveraged = [prop_map[pid] for pid in actor.portfolio
                         if pid in prop_map and prop_map[pid].mortgage_balance > 0]
            a_avg_rate = round(
                sum(p.mortgage_rate for p in leveraged) / len(leveraged) * 100, 2
            ) if leveraged else None

            # void count
            a_void_count = sum(1 for pid in actor.portfolio
                               if pid in prop_map and prop_map[pid].void_ticks_remaining > 0)

            # refi headroom total
            a_refi_total = round(sum(p["refi_headroom"] for p in a_portfolio), 0)

            # avg capital growth %
            pnl_pcts = [p["pnl_pct"] for p in a_portfolio]
            a_avg_cap_growth = round(sum(pnl_pcts) / len(pnl_pcts), 1) if pnl_pcts else 0.0

            # cash-on-cash: annual net CF / cash deployed (initial_wealth - current cash)
            cash_deployed = round(actor.initial_wealth - actor.cash, 0)
            a_coc = round(a_annual_net / cash_deployed * 100, 1) if cash_deployed > 0 else None

            actors_state[a_id] = {
                "name": actor.name,
                "cash": round(actor.cash, 0),
                "strategy": actor.strategy,
                "portfolio": a_portfolio,
                "avg_mortgage_rate": a_avg_rate,
                "void_count": a_void_count,
                "total_void_losses": round(actor.total_void_losses, 0),
                "total_maintenance_costs": round(actor.total_maintenance_costs, 0),
                "portfolio_debt": round(a_mtg_tot, 0),
                "cash_flow": {"rent": round(a_rent, 0), "mortgage": round(a_mtg, 0),
                              "net": round(a_rent - a_mtg, 0)},
                "wealth_delta": a_delta,
                "analytics": {
                    "gross_yield_pct": a_gross_yield,
                    "unrealised_gain": a_unrealised,
                    "return_on_equity": a_roe,
                    "cash_on_cash": a_coc,
                    "avg_capital_growth_pct": a_avg_cap_growth,
                    "refi_headroom_total": a_refi_total,
                    "epc_risk": {"count": len(a_epc_risk_props),
                                 "value": round(sum(p["value"] for p in a_epc_risk_props), 0)},
                    "archetype_concentration": [
                        {"archetype": a, "pct": round(v / a_arch_total * 100, 1), "value": round(v, 0)}
                        for a, v in sorted(a_arch.items(), key=lambda x: -x[1])
                    ],
                    "region_concentration_pct": round(
                        max(a_regions.values()) / (sum(a_regions.values()) or 1) * 100, 1
                    ) if a_regions else 0.0,
                    "bedroom_mix": [
                        {"label": k, "count": v, "pct": round(v / a_beds_total * 100, 1)}
                        for k, v in sorted(a_beds.items())
                    ],
                },
            }

        available_props = []
        for p in self.state.properties:
            if p.id not in owned_all:
                gross_yield = round((p.rent * 12) / p.current_value * 100, 1)
                affordable = player and player.cash >= (p.current_value * 0.25 + _calculate_sdlt(p.current_value))
                available_props.append({
                    "id": p.id, "region": p.region,
                    "value": round(p.current_value, 0),
                    "sdlt": round(_calculate_sdlt(p.current_value), 0),
                    "gross_yield_pct": gross_yield,
                    "rent_monthly": round(p.rent, 0),
                    "epc_band": p.epc_band,
                    "epc_label": chr(64 + p.epc_band),
                    "archetype": p.archetype,
                    "bedrooms": p.bedrooms,
                    "affordable": affordable,
                    "age": p.age,
                    "void_risk_pct": void_risk_pct(p, self.state.macro_history, self.state.epc_mandate_announced),
                    "maintenance_risk": maintenance_risk_label(p),
                    "maintenance_reserve": expected_maintenance_reserve(p),
                    "is_auction": p.is_auction,
                })

        # Net worth delta vs previous tick
        wealth_delta = None
        if player and len(self._wealth_history) >= 2:
            curr_w = self._wealth_history[-1].get("player", 0)
            prev_w = self._wealth_history[-2].get("player", 0)
            delta_total = round(curr_w - prev_w, 0)
            rent_per_turn = round(total_rent * 6, 0)
            mortgage_per_turn = round(total_mortgage_cost * 6, 0)
            wealth_delta = {
                "total": delta_total,
                "rent": rent_per_turn,
                "mortgage": mortgage_per_turn,
                "appreciation": round(delta_total - rent_per_turn + mortgage_per_turn, 0),
            }

        # Portfolio concentration by region
        concentration = []
        if player:
            region_values: dict[str, float] = {}
            for pid in player.portfolio:
                p = prop_map.get(pid)
                if p:
                    region_values[p.region] = region_values.get(p.region, 0) + p.current_value
            total_pv = sum(region_values.values()) or 1.0
            concentration = [
                {"region": r, "pct": round(v / total_pv * 100, 1), "value": round(v, 0)}
                for r, v in sorted(region_values.items(), key=lambda x: -x[1])
            ]

        # Portfolio-level LTV and ICR
        total_portfolio_value = sum(
            prop_map[pid].current_value for pid in (player.portfolio if player else []) if pid in prop_map
        )
        total_mortgage_balance_pf = sum(
            prop_map[pid].mortgage_balance for pid in (player.portfolio if player else []) if pid in prop_map
        )
        portfolio_ltv_pct = round(total_mortgage_balance_pf / total_portfolio_value * 100, 1) if total_portfolio_value > 0 else 0.0
        annual_rent = total_rent * 12
        annual_mortgage_cost = total_mortgage_cost * 12
        icr = round(annual_rent / annual_mortgage_cost, 2) if annual_mortgage_cost > 0 else None

        # Portfolio analytics
        player_equity    = total_portfolio_value - total_mortgage_balance_pf
        unrealised_gain  = round(sum(prop_map[pid].current_value - prop_map[pid].base_value
                                     for pid in (player.portfolio if player else []) if pid in prop_map), 0)
        gross_yield_pct  = round(total_rent * 12 / total_portfolio_value * 100, 1) if total_portfolio_value > 0 else 0.0
        annual_net_cf    = (total_rent - total_mortgage_cost) * 12
        return_on_equity = round(annual_net_cf / player_equity * 100, 1) if player_equity > 0 else None
        _epc_threshold   = 4 if self.state.epc_mandate_announced else 6
        epc_risk_props   = [prop_map[pid] for pid in (player.portfolio if player else [])
                            if pid in prop_map and prop_map[pid].epc_band >= _epc_threshold]
        epc_risk = {"count": len(epc_risk_props),
                    "value": round(sum(p.current_value for p in epc_risk_props), 0)}
        arch_values: dict[str, float] = {}
        for pid in (player.portfolio if player else []):
            p = prop_map.get(pid)
            if p:
                arch_values[p.archetype] = arch_values.get(p.archetype, 0) + p.current_value
        arch_total = sum(arch_values.values()) or 1.0
        archetype_concentration = [
            {"archetype": a, "pct": round(v / arch_total * 100, 1), "value": round(v, 0)}
            for a, v in sorted(arch_values.items(), key=lambda x: -x[1])
        ]

        # Rate stress test (impact of +1% and +2% rate rise on monthly cash flow)
        total_mortgage_balance = sum(
            prop_map[pid].mortgage_balance
            for pid in (player.portfolio if player else [])
            if pid in prop_map
        )
        net_cf = round(total_rent - total_mortgage_cost, 0)
        rate_stress = {
            "has_mortgages": total_mortgage_balance > 0,
            "current_net": net_cf,
            "stress_1pct_net": round(net_cf - total_mortgage_balance * 0.01 / 12, 0),
            "stress_2pct_net": round(net_cf - total_mortgage_balance * 0.02 / 12, 0),
        }

        data = {
            "tick": self.state.tick,
            "total_ticks": self.turns,
            "mode": self.mode,
            "scenario": self.state.current_scenario,
            "macro_history": self._macro_history_export,
            "wealth_history": self._wealth_history,
            "current_events": [e for e in current_events
                                if e["type"] in ("rate_shock_up", "rate_shock_down",
                                                  "rate_rise", "rate_cut",
                                                  "price_crash", "price_surge",
                                                  "rent_surge", "rent_squeeze",
                                                  "epc_mandate", "epc_warning",
                                                  "epc_void")],
            "actors": actors_data,
            "actors_state": actors_state,
            "last_actions": dict(self.state.last_ai_actions),
            "x_labels": x_labels,
            "axis_ranges": self._axis_ranges,
            "preamble_macro": self.preamble_macro,
            "era_label": self.era_label if is_final else None,
            "start_year": self.state.start_year if is_final else None,
            "final_year": self.historical_slice[-1][0] if is_final else None,
            "player_state": {
                "cash": round(player.cash, 0) if player else 0,
                "portfolio": player_portfolio,
                "available": available_props,
                "tick": self.state.tick,
                "cash_flow": {
                    "rent": round(total_rent, 0),
                    "mortgage": round(total_mortgage_cost, 0),
                    "net": round(total_rent - total_mortgage_cost, 0),
                },
                "wealth_delta": wealth_delta,
                "concentration": concentration,
                "rate_stress": rate_stress,
                "portfolio_ltv_pct": portfolio_ltv_pct,
                "icr": icr,
                "analytics": {
                    "gross_yield_pct": gross_yield_pct,
                    "unrealised_gain": unrealised_gain,
                    "return_on_equity": return_on_equity,
                    "cash_on_cash": round(annual_net_cf / (player.initial_wealth - player.cash) * 100, 1)
                                    if player and (player.initial_wealth - player.cash) > 0 else None,
                    "avg_capital_growth_pct": round(
                        sum((prop_map[pid].current_value - prop_map[pid].base_value) / prop_map[pid].base_value * 100
                            for pid in player.portfolio if pid in prop_map and prop_map[pid].base_value > 0)
                        / len(player.portfolio), 1) if player and player.portfolio else 0.0,
                    "refi_headroom_total": round(sum(p["refi_headroom"] for p in player_portfolio), 0),
                    "epc_risk": epc_risk,
                    "archetype_concentration": archetype_concentration,
                },
            },
        }
        if is_final:
            data["leaderboard"]   = self.scoring.leaderboard(self.state)
            data["player_eval"]   = self._player_eval
        if self._bus is not None:
            self._bus.set_state(data)
        else:
            os.makedirs(os.path.dirname(TURN_STATE_PATH), exist_ok=True)
            with open(TURN_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f)

    def run(self):
        trace = []
        if self._bus is None:
            os.makedirs(os.path.dirname(TURN_STATE_PATH), exist_ok=True)

        # Write intro state so the dashboard can show opponent info before the game starts
        intro_actors = {
            a_id: {"name": actor.name, "strategy": actor.strategy}
            for a_id, actor in self.state.actors.items()
            if a_id != "player"
        }
        player_actor = self.state.actors.get("player")
        intro_data = {
            "state": "intro",
            "actors": intro_actors,
            "total_ticks": self.turns,
            "player_cash": round(player_actor.cash, 0) if player_actor else 0,
            "preamble_macro": self.preamble_macro,
        }

        if self._bus is not None:
            self._bus.set_state(intro_data)
            print("Waiting for player to start game… (in-process bus)", flush=True)
            self._bus.wait_ready()
            # Apply player name entered on the intro screen
            player_name = self._bus.get_player_name()
            if player_name and player_name != "You":
                self.state.actors["player"].name = player_name
        else:
            if os.path.exists(READY_PATH):
                os.remove(READY_PATH)
            with open(TURN_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(intro_data, f)
            print(f"Waiting for player to start game… (looking for {READY_PATH})", flush=True)
            while not os.path.exists(READY_PATH):
                time.sleep(0.5)
            os.remove(READY_PATH)
            with open(TURN_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)

        print("Ready signal received — starting game.", flush=True)

        prev_entry = None
        cumulative_inflation = 100.0

        # Seed tick-0 snapshot so charts show the starting baseline
        first_entry = self.historical_slice[0]
        self._macro_history_export.append({
            "tick": 0,
            "price_index": round(first_entry[2], 2),
            "rate": round(first_entry[3], 2),
            "rent_growth": round(first_entry[4], 2),
            "cumulative_inflation": 100.0,
        })
        prop_map_t0 = {p.id: p for p in self.state.properties}
        wealth_snap_t0 = {"tick": 0}
        for actor_id, actor in self.state.actors.items():
            equity_t0 = sum(
                prop_map_t0[pid].current_value - prop_map_t0[pid].mortgage_balance
                for pid in actor.portfolio if pid in prop_map_t0
            )
            wealth_snap_t0[actor_id]            = round(actor.cash + equity_t0, 2)
            wealth_snap_t0[f"{actor_id}_pv"]   = round(equity_t0, 2)
            wealth_snap_t0[f"{actor_id}_cash"] = round(actor.cash, 2)
        self._wealth_history.append(wealth_snap_t0)

        for i in range(self.turns):
            if self._bus and self._bus.restart_requested():
                print("Restart requested — aborting current game.", flush=True)
                return {"leaderboard": [], "restarted": True}
            self.state.advance_tick()
            tick = self.state.tick
            curr_entry = self.historical_slice[i]

            self._apply_macro(curr_entry)
            _, _, price_index, rate, rent_growth, cpi = curr_entry
            cumulative_inflation *= (1 + cpi / 100 / 2)

            tick_events = []
            tick_events += detect_events(prev_entry, curr_entry, tick)
            prev_price_index = prev_entry[2] if prev_entry else price_index
            rate_delta = (curr_entry[3] - prev_entry[3]) if prev_entry else 0.0
            hpi_delta_pct = (price_index - prev_price_index) / prev_price_index * 100 if prev_entry else 0.0
            self.state.current_scenario = label_from_deltas(rate_delta, hpi_delta_pct)
            tick_events.append({
                "type": "scenario_advance",
                "tick": tick,
                "scenario": self.state.current_scenario,
                "detail": f"Scenario: {self.state.current_scenario}",
            })

            tick_events += self.property_model.update(self.state)

            tick_events += self.void_maintenance.step(self.state, tick)

            tick_events += self.actors.step(self.state, tick)

            ai_events = self.ai.step(self.state, tick)
            for event in ai_events:
                self._execute_action(event)
                actor_id = event.get("actor_id")
                action   = event.get("action", "hold")
                pid      = event.get("property_id")
                if actor_id:
                    actor = self.state.actors.get(actor_id)
                    actually_bought   = action == "buy"     and actor and pid in actor.portfolio
                    actually_sold     = action == "sell"    and actor and pid not in actor.portfolio
                    actually_upgraded = action == "upgrade" and actor and pid in actor.portfolio
                    actually_refi     = action == "refi"    and actor and pid in actor.portfolio
                    self.state.last_ai_actions[actor_id] = (
                        f"bought {pid}"   if actually_bought   else
                        f"sold {pid}"     if actually_sold     else
                        f"upgraded {pid}" if actually_upgraded else
                        f"refi {pid}"     if actually_refi     else "hold"
                    )
            tick_events += ai_events

            # Position-aware advice for player
            player_actor    = self.state.actors.get("player")
            owned_now       = {pid for a in self.state.actors.values() for pid in a.portfolio}
            avail_now       = [p for p in self.state.properties if p.id not in owned_now]
            ticks_remaining = self.turns - tick

            # Current standings
            cur_scores      = self.scoring.compute_scores(self.state)
            sorted_scores   = sorted(cur_scores.values(), key=lambda s: s["final_score"], reverse=True)
            player_score    = cur_scores.get("player", {}).get("final_score", 0)
            player_rank     = next((i + 1 for i, s in enumerate(sorted_scores)
                                    if s["actor_id"] == "player"), len(sorted_scores))
            leader_score    = sorted_scores[0]["final_score"] if sorted_scores else player_score
            score_gap       = max(0, leader_score - player_score)
            opp_strategies  = [a.strategy for aid, a in self.state.actors.items()
                                if aid != "player"]

            adv_action, adv_prop, _, adv_strategy = _select_advice(
                self.state, player_actor, avail_now, self.ai,
                player_rank, score_gap, ticks_remaining, opp_strategies,
            )

            player_events = self.player_choices.step(self.state, tick)
            for event in player_events:
                self._execute_action(event)
                actor_id = event.get("actor_id")
                action   = event.get("action", "hold")
                pid      = event.get("property_id")
                if actor_id:
                    self.state.last_ai_actions[actor_id] = (
                        f"bought {pid}"    if action == "buy"      else
                        f"sold {pid}"      if action == "sell"     else
                        f"upgraded {pid}"  if action == "upgrade"  else
                        f"refi {pid}"      if action == "refi"     else
                        f"renovated {pid}" if action == "renovate" else "hold"
                    )
            tick_events += player_events

            # Record per-turn evaluation
            year, half, *_ = curr_entry
            p_action = self.state.last_ai_actions.get("player", "hold")
            self._player_eval.append({
                "tick":          tick,
                "label":         f"{year} H{half}",
                "scenario":      self.state.current_scenario,
                "rate":          round(rate, 2),
                "player":        p_action,
                "advice":        f"buy {adv_prop}"     if adv_action == "buy"     and adv_prop
                                 else f"upgrade {adv_prop}" if adv_action == "upgrade" and adv_prop
                                 else adv_action,
                "adv_strategy":  adv_strategy,
                "rank":          player_rank,
                "score_gap":     round(score_gap, 0),
                "ticks_left":    ticks_remaining,
                "comment":       _eval_comment(
                                     p_action, adv_action, adv_prop,
                                     rate, self.state.current_scenario,
                                     player_rank, score_gap, adv_strategy, ticks_remaining,
                                 ),
            })

            tick_events += self.branching.step(self.state, tick)
            tick_events += self.scenario_events.step(self.state, tick)

            # Tick 1: void any F/G properties — minimum standard is EPC E at game start
            if tick == 1:
                _owner_map = {pid: aid
                              for aid, a in self.state.actors.items()
                              for pid in a.portfolio}
                for prop in self.state.properties:
                    if prop.epc_band >= 6 and not prop.epc_void:
                        prop.epc_void = True
                        prop.void_ticks_remaining = 999
                        owner = _owner_map.get(prop.id)
                        tick_events.append({
                            "type": "epc_void",
                            "tick": tick,
                            "property_id": prop.id,
                            "actor_id": owner,
                            "detail": f"{prop.id} void — EPC {chr(64 + prop.epc_band)} is below the minimum E standard (upgrade to re-let)",
                        })

            # EPC mandate: randomly announced between ticks 7–12
            if tick == self._epc_mandate_tick:
                self._epc_mandate_announced = True
                self.state.epc_mandate_announced = True
                _owner_map = {pid: aid
                              for aid, a in self.state.actors.items()
                              for pid in a.portfolio}
                tick_events.append({
                    "type": "epc_mandate",
                    "tick": tick,
                    "detail": f"Government mandates EPC C minimum — all EPC properties must reach C within 2 years",
                })
                for prop in self.state.properties:
                    if prop.epc_band >= 4:
                        self._epc_warned[prop.id] = tick
                        owner = _owner_map.get(prop.id)
                        tick_events.append({
                            "type": "epc_warning",
                            "tick": tick,
                            "property_id": prop.id,
                            "actor_id": owner,
                            "detail": f"{prop.id} (EPC {chr(64 + prop.epc_band)}) must reach C within 2 years or it will go void",
                        })

            # EPC void: post-mandate, non-compliant D–G properties go void after grace period
            for prop in list(self.state.properties):
                warned_at = self._epc_warned.get(prop.id)
                if warned_at and tick == warned_at + EPC_GRACE_TICKS and prop.epc_band >= 4:
                    if not prop.epc_void:
                        prop.epc_void = True
                        prop.void_ticks_remaining = 999
                        owner = next(
                            (aid for aid, a in self.state.actors.items() if prop.id in a.portfolio),
                            None,
                        )
                        tick_events.append({
                            "type": "epc_void",
                            "tick": tick,
                            "property_id": prop.id,
                            "actor_id": owner,
                            "detail": f"{prop.id} gone void — EPC {chr(64 + prop.epc_band)} non-compliant with mandate (upgrade to C or better to re-let)",
                        })

            self.state.event_log.extend(tick_events)
            self.state.macro_history.append(MacroSnapshot(
                tick=tick,
                scenario=self.state.current_scenario,
                price_index=self.state.macro.price_index,
                interest_rate=self.state.macro.interest_rate,
                rent_growth=self.state.macro.rent_growth,
                events=[e for e in tick_events if e["type"] in
                        ("rate_shock_up", "rate_shock_down", "price_crash",
                         "price_surge", "rent_surge", "rent_squeeze")],
            ))

            self._macro_history_export.append({
                "tick": tick,
                "price_index": round(self.state.macro.price_index, 2),
                "rate": round(rate, 2),
                "rent_growth": round(rent_growth, 2),
                "cumulative_inflation": round(cumulative_inflation, 2),
            })
            wealth_snap = {"tick": tick}
            prop_map_snap = {p.id: p for p in self.state.properties}
            for actor_id, actor in self.state.actors.items():
                equity = sum(
                    prop_map_snap[pid].current_value - prop_map_snap[pid].mortgage_balance
                    for pid in actor.portfolio if pid in prop_map_snap
                )
                wealth_snap[actor_id]            = round(actor.cash + equity, 2)
                wealth_snap[f"{actor_id}_pv"]   = round(equity, 2)
                wealth_snap[f"{actor_id}_cash"] = round(actor.cash, 2)
            self._wealth_history.append(wealth_snap)

            # Remove stale auction properties before replenishing
            self._remove_stale_auction_properties()

            # Keep a minimum number of properties available on the market
            owned_ids = {pid for a in self.state.actors.values() for pid in a.portfolio}
            available_count = sum(1 for p in self.state.properties if p.id not in owned_ids)
            if available_count < _MARKET_MIN_AVAILABLE:
                self._replenish_market(_MARKET_TARGET - available_count)

            # Schedule one auction property every 4 ticks — only when an eligible AI is playing
            _AUCTION_STRATEGIES = {"value_add", "brrr", "yield"}
            _auction_eligible = any(
                a.strategy in _AUCTION_STRATEGIES
                for a in self.state.actors.values()
                if a.id != "player"
            )
            if tick % 6 == 0 and _auction_eligible:
                self._add_auction_property()

            is_final = (i == self.turns - 1)
            self._write_turn_state(tick_events, is_final=is_final)
            trace.append({"tick": tick, "events": tick_events})

            # Sleep turn_delay (or 5s on final), aborting early if client disconnects.
            sleep_secs = 5 if is_final else self.turn_delay
            sleep_end = time.time() + sleep_secs
            while time.time() < sleep_end:
                if self._bus and not self._bus.is_client_connected():
                    print("Client disconnected — ending game.", flush=True)
                    self._bus.set_game_active(False)
                    return {"leaderboard": [], "aborted": True}
                time.sleep(1)

            # Wait for player to submit their action before advancing to the next tick.
            # Without this, the kernel races ahead and the player only has ~2 seconds.
            if not is_final:
                if self._bus is not None:
                    action_deadline = time.time() + 90
                    while not self._bus.has_action():
                        self._bus.wait_action(timeout=3)
                        if self._bus.has_action():
                            break
                        if not self._bus.is_client_connected():
                            print("Client disconnected during action wait — ending game.", flush=True)
                            self._bus.set_game_active(False)
                            return {"leaderboard": [], "aborted": True}
                        if time.time() > action_deadline:
                            print(f"Action timeout on tick {tick} — auto-holding.", flush=True)
                            self._bus.submit_action("hold", None, 0.0)
                            break
                else:
                    deadline = time.time() + 60
                    while time.time() < deadline:
                        try:
                            with open(PLAYER_ACTION_PATH, encoding="utf-8") as f:
                                data = json.load(f)
                            if data.get("action"):
                                break
                        except (FileNotFoundError, json.JSONDecodeError):
                            pass
                        time.sleep(0.3)

            prev_entry = curr_entry

        if self._bus is not None:
            self._bus.set_game_active(False)
        leaderboard = self.scoring.leaderboard(self.state)
        return {"trace": trace, "leaderboard": leaderboard, "era_label": self.era_label, "start_year": self.state.start_year}

    def _execute_action(self, event):
        actor_id   = event.get("actor_id")
        action     = event.get("action")
        property_id = event.get("property_id")
        ltv        = event.get("ltv", 0.0)

        if not actor_id or action in ("hold", None) or not property_id:
            return

        actor = self.state.actors.get(actor_id)
        if not actor:
            return

        prop_map  = {p.id: p for p in self.state.properties}
        owned_all = {pid for a in self.state.actors.values() for pid in a.portfolio}
        prop = prop_map.get(property_id)
        if not prop:
            return

        if action == "sell" and property_id in actor.portfolio:
            agent_fee = prop.current_value * 0.015
            net = prop.current_value - prop.mortgage_balance - agent_fee
            actor.cash += net
            actor.total_transaction_costs += agent_fee
            prop.mortgage_balance = 0.0
            prop.mortgage_rate = 0.0
            prop.is_fixed_rate = False
            actor.portfolio.remove(property_id)

        elif action == "buy" and property_id not in owned_all:
            if prop.is_auction:
                bid_premium = event.get("bid_premium", 0.0)
                bid_price   = round(prop.current_value * (1 + bid_premium))
                if actor_id == "player":
                    # Competitive resolution: player vs eligible AI bids
                    _AUCTION_STRATEGIES = {"value_add", "brrr", "yield"}
                    ai_bids = {}
                    for aid, a in self.state.actors.items():
                        if aid != "player" and a.strategy in _AUCTION_STRATEGIES:
                            premium = self.ai.ai_bid_premium(aid, a, prop, self.state)
                            if premium is not None:
                                ai_bids[aid] = round(prop.current_value * (1 + premium))
                    best_ai_bid = max(ai_bids.values()) if ai_bids else 0
                    player_wins = bid_price >= best_ai_bid  # ties go to player
                    can_buy = player_wins and actor.cash >= bid_price
                else:
                    # AI auction buy already resolved in ai.step() — direct cash purchase
                    can_buy = actor.cash >= bid_price
                if can_buy:
                    actor.cash -= bid_price
                    actor.total_transaction_costs += round(bid_price * 0.01)
                    prop.mortgage_balance = 0.0
                    prop.mortgage_rate = 0.0
                    prop.is_fixed_rate = False
                    prop.void_ticks_remaining = _VOID_BY_ARCHETYPE.get(prop.archetype, 0)
                    actor.portfolio.append(property_id)
            else:
                deposit      = prop.current_value * (1 - ltv)
                sdlt         = _calculate_sdlt(prop.current_value)
                total_outlay = deposit + sdlt
                if actor.cash >= total_outlay:
                    actor.cash -= total_outlay
                    actor.total_transaction_costs += sdlt
                    prop.mortgage_balance = prop.current_value * ltv
                    prop.mortgage_rate = self.state.macro.interest_rate + MORTGAGE_SPREAD
                    prop.is_fixed_rate = True
                    prop.fixed_ticks_remaining = 4
                    prop.void_ticks_remaining = _VOID_BY_ARCHETYPE.get(prop.archetype, 0)
                    actor.portfolio.append(property_id)

        elif action == "upgrade" and property_id in actor.portfolio:
            old_band = prop.epc_band
            cost = _epc_upgrade_cost(old_band)
            if cost > 0 and actor.cash >= cost:
                actor.cash -= cost
                actor.total_transaction_costs += cost
                prop.epc_band = max(1, old_band - 2)
                prop.rent *= 1.10
                uplift = _EPC_VALUE_UPLIFT.get(old_band, 0)
                if uplift:
                    prop.current_value = round(prop.current_value * (1 + uplift) / 1000) * 1000
                prop.base_value = prop.current_value  # rebase so HPI compounds from post-upgrade value
                compliant_threshold = 4 if self._epc_mandate_announced else 6
                if prop.epc_void and prop.epc_band < compliant_threshold:
                    prop.epc_void = False
                    prop.void_ticks_remaining = 0

        elif action == "renovate" and property_id in actor.portfolio:
            if not prop.renovated:
                cost = round(prop.current_value * 0.10)
                if actor.cash >= cost:
                    actor.cash -= cost
                    actor.total_transaction_costs += cost
                    prop.rent *= 1.15
                    prop.current_value *= 1.08
                    prop.renovated = True

        elif action == "refi" and property_id in actor.portfolio:
            if prop.fixed_ticks_remaining == 0:
                new_balance = prop.current_value * ltv
                released = new_balance - prop.mortgage_balance
                if released > 0:
                    fee = 1_500
                    actor.cash += released - fee
                    actor.total_transaction_costs += fee
                    prop.mortgage_balance = new_balance
                    prop.mortgage_rate = self.state.macro.interest_rate + MORTGAGE_SPREAD
                    prop.is_fixed_rate = True
                    prop.fixed_ticks_remaining = 4

    def _replenish_market(self, count: int) -> None:
        """Add new properties to the market scaled to current price index."""
        # Price and rent multipliers vs standard BTL by archetype
        _ARCHETYPE_PRICE_MULT = {"btl": 1.0, "value_add": 0.80, "hmo": 1.30,
                                  "short_let": 1.10, "new_build": 1.15}
        # HMOs yield ~2.2x BTL (per-room income); short-lets ~1.6x; new_builds slightly below market
        _ARCHETYPE_YIELD_MULT = {"btl": 1.0, "value_add": 1.05, "hmo": 2.20,
                                  "short_let": 1.60, "new_build": 0.90}
        price_factor = self.state.macro.price_index / 100.0
        for _ in range(count):
            region = _MARKET_REGIONS[self._next_market_id % len(_MARKET_REGIONS)]
            profile = _MARKET_REGION_PROFILES[region]
            archetype = random.choice(["btl", "btl", "btl", "value_add", "hmo", "short_let", "new_build"])
            base_value = _MARKET_NATIONAL_BASE * profile["price_level"] * price_factor
            value = round(base_value * _ARCHETYPE_PRICE_MULT.get(archetype, 1.0) / 1000) * 1000
            yield_mult = _ARCHETYPE_YIELD_MULT.get(archetype, 1.0)
            rent  = round(value * profile["annual_yield"] * yield_mult / 12)
            epc_band = random.choice(profile["epc_bands"])
            epc_discount = _EPC_PRICE_DISCOUNT.get(epc_band, 0)
            value = round(value * (1 - epc_discount) / 1000) * 1000
            bedrooms = {"btl": 3, "value_add": 3, "hmo": 5, "short_let": 1, "new_build": 2}.get(archetype, 3)
            prop = Property(
                id=f"mk{self._next_market_id:03d}",
                region=region,
                base_value=float(value),
                current_value=float(value),
                rent=float(rent),
                archetype=archetype,
                epc_band=epc_band,
                age=random.randint(5, 80),
                bedrooms=bedrooms,
                hpi_factor=profile["hpi_factor"],
            )
            self.state.properties.append(prop)
            self._next_market_id += 1

    def _add_auction_property(self) -> None:
        """Add one auction property at 25% below market value."""
        region = _MARKET_REGIONS[self._next_market_id % len(_MARKET_REGIONS)]
        profile = _MARKET_REGION_PROFILES[region]
        price_factor = self.state.macro.price_index / 100.0
        archetype = random.choice(["btl", "value_add", "hmo"])
        _PRICE_MULT = {"btl": 1.0, "value_add": 0.80, "hmo": 1.30}
        _YIELD_MULT = {"btl": 1.0, "value_add": 1.05, "hmo": 2.20}
        market_value = _MARKET_NATIONAL_BASE * profile["price_level"] * price_factor * _PRICE_MULT[archetype]
        epc_band = random.choice(profile["epc_bands"])
        epc_discount = _EPC_PRICE_DISCOUNT.get(epc_band, 0)
        auction_value = round(market_value * 0.75 * (1 - epc_discount) / 1000) * 1000
        rent = round(market_value * 0.75 * profile["annual_yield"] * _YIELD_MULT[archetype] / 12)
        bedrooms = {"btl": 3, "value_add": 3, "hmo": 5}.get(archetype, 3)
        prop = Property(
            id=f"auc{self._next_market_id:03d}",
            region=region,
            base_value=float(auction_value),
            current_value=float(auction_value),
            rent=float(rent),
            archetype=archetype,
            epc_band=epc_band,
            age=random.randint(20, 80),
            bedrooms=bedrooms,
            hpi_factor=profile["hpi_factor"],
            is_auction=True,
        )
        self.state.properties.append(prop)
        self._next_market_id += 1

    def _remove_stale_auction_properties(self) -> None:
        """Remove unsold auction properties from the market."""
        owned = {pid for a in self.state.actors.values() for pid in a.portfolio}
        self.state.properties = [
            p for p in self.state.properties
            if not p.is_auction or p.id in owned
        ]
