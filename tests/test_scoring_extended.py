import pytest
from scoring import ScoringEngine
from state import Property, ActorState, SimulationState, MacroState


def _make_state():
    p1 = Property(id="p1", region="London", base_value=300_000,
                  current_value=330_000, rent=1_500.0, epc_band=3,
                  mortgage_balance=0.0)
    p2 = Property(id="p2", region="Leeds",  base_value=150_000,
                  current_value=140_000, rent=700.0,  epc_band=5,
                  mortgage_balance=50_000.0)
    actor = ActorState(id="a1", name="Inv", cash=80_000.0, risk_appetite=0.5,
                       portfolio=["p1", "p2"],
                       total_rent_received=20_000.0,
                       total_mortgage_paid=8_000.0,
                       total_transaction_costs=5_000.0,
                       initial_wealth=500_000.0)
    state = SimulationState()
    state.macro = MacroState()
    state.properties = [p1, p2]
    state.actors = {"a1": actor}
    return state, actor


def test_risk_score_between_0_and_100():
    state, actor = _make_state()
    eng = ScoringEngine()
    score = eng.compute_risk_score(actor, state.properties)
    assert 0 <= score <= 100


def test_high_epc_and_high_ltv_gives_higher_risk():
    state, actor = _make_state()
    eng = ScoringEngine()
    base = eng.compute_risk_score(actor, state.properties)
    state.properties[0].epc_band = 7
    state.properties[1].mortgage_balance = 140_000
    worse = eng.compute_risk_score(actor, state.properties)
    assert worse > base


def test_leaderboard_includes_risk_and_return_fields():
    state, _ = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    assert "risk_score" in lb[0]
    assert "income_return" in lb[0]
    assert "capital_return" in lb[0]
    assert "risk_adjusted_return" in lb[0]


def test_income_return_matches_rent_received():
    state, actor = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    assert lb[0]["income_return"] == pytest.approx(actor.total_rent_received)


def test_capital_return_is_portfolio_gain():
    state, actor = _make_state()
    eng = ScoringEngine()
    lb = eng.leaderboard(state)
    # p1 gained 30k, p2 lost 10k, net = 20k
    assert lb[0]["capital_return"] == pytest.approx(20_000, rel=1e-3)


def test_empty_portfolio_risk_score_is_neutral():
    state, actor = _make_state()
    actor.portfolio = []
    eng = ScoringEngine()
    score = eng.compute_risk_score(actor, state.properties)
    assert score == 50.0
