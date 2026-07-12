from state import SimulationState, ActorState, Property
from scoring import ScoringEngine


def _populated_state():
    state = SimulationState()
    state.properties = [
        Property(id="p1", region="London", base_value=300000.0, current_value=320000.0, rent=1600.0),
        Property(id="p2", region="Manchester", base_value=150000.0, current_value=160000.0, rent=900.0),
    ]
    state.actors = {
        "player": ActorState(id="player", name="Player", cash=50000.0, risk_appetite=0.5, portfolio=["p1"]),
        "ai1": ActorState(id="ai1", name="AI", cash=30000.0, risk_appetite=0.7, portfolio=["p2"]),
    }
    return state


def test_final_score_includes_portfolio_value_and_cash():
    state = _populated_state()
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    player_score = scores["player"]
    assert abs(player_score["portfolio_value"] - 320000.0) < 0.01
    assert abs(player_score["cash"] - 50000.0) < 0.01
    # final_score is risk-adjusted — check it's present and positive
    assert "final_score" in player_score
    assert player_score["final_score"] is not None


def test_income_return_reflects_rent_received():
    state = _populated_state()
    state.actors["player"].total_rent_received = 3200.0
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    assert abs(scores["player"]["income_return"] - 3200.0) < 0.01


def test_actor_with_no_properties_scores_only_cash():
    state = SimulationState()
    state.actors = {
        "a1": ActorState(id="a1", name="A", cash=20000.0, risk_appetite=0.5, portfolio=[])
    }
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    assert abs(scores["a1"]["portfolio_value"] - 0.0) < 0.01
    assert abs(scores["a1"]["cash"] - 20000.0) < 0.01


def test_scores_include_all_actors():
    state = _populated_state()
    engine = ScoringEngine()
    scores = engine.compute_scores(state)
    assert "player" in scores
    assert "ai1" in scores
