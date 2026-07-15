import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from state import SimulationState, Property, ActorState, MacroState
from kernel import SimulationKernel
from scoring import ScoringEngine


class _CaptureBus:
    """Minimal bus that captures the last state passed to set_state."""
    def __init__(self):
        self._state = None

    def set_state(self, data):
        self._state = data

    @property
    def state(self):
        return self._state


def _minimal_kernel(bus):
    k = SimulationKernel.__new__(SimulationKernel)
    k.state = SimulationState()
    k.state.macro = MacroState(price_index=100.0, interest_rate=0.05, rent_growth=0.03)
    k.state.actors = {}
    k.state.properties = []
    k.state.tick = 1
    k.state.current_scenario = "normal"
    k.state.last_ai_actions = {}
    k.state.macro_history = []
    k.turns = 20
    k.mode = "student"
    k.historical_slice = [(2010, 1, 100.0, 5.0, 2.0, 2.5)]
    k.era_label = "2010s"
    k._wealth_history = []
    k._macro_history_export = []
    k._player_eval = []
    k._axis_ranges = {"hpi": [80, 120], "rate": [3, 7], "rent": [1, 4]}
    k.scoring = ScoringEngine()
    k._bus = bus
    return k


def test_available_includes_is_auction():
    bus = _CaptureBus()
    k = _minimal_kernel(bus)
    prop = Property(
        id="auc001", region="North", base_value=100_000, current_value=100_000,
        rent=500.0, is_auction=True,
    )
    k.state.properties = [prop]
    k._write_turn_state(current_events=[])
    available = bus.state["player_state"]["available"]
    assert len(available) == 1
    assert available[0]["is_auction"] is True


def test_available_is_auction_false_by_default():
    bus = _CaptureBus()
    k = _minimal_kernel(bus)
    prop = Property(
        id="p01", region="North", base_value=150_000, current_value=150_000, rent=700.0,
    )
    k.state.properties = [prop]
    k._write_turn_state(current_events=[])
    available = bus.state["player_state"]["available"]
    assert len(available) == 1
    assert available[0]["is_auction"] is False


def test_portfolio_includes_renovated():
    bus = _CaptureBus()
    k = _minimal_kernel(bus)
    prop = Property(
        id="p01", region="North", base_value=150_000, current_value=150_000,
        rent=700.0, renovated=True,
    )
    actor = ActorState(id="player", name="Player", cash=50_000, risk_appetite=0.5)
    actor.portfolio.append("p01")
    actor.initial_wealth = 200_000
    k.state.properties = [prop]
    k.state.actors = {"player": actor}
    k._write_turn_state(current_events=[])
    portfolio = bus.state["player_state"]["portfolio"]
    assert len(portfolio) == 1
    assert portfolio[0]["renovated"] is True


def test_portfolio_renovated_false_by_default():
    bus = _CaptureBus()
    k = _minimal_kernel(bus)
    prop = Property(
        id="p01", region="North", base_value=150_000, current_value=150_000, rent=700.0,
    )
    actor = ActorState(id="player", name="Player", cash=50_000, risk_appetite=0.5)
    actor.portfolio.append("p01")
    actor.initial_wealth = 200_000
    k.state.properties = [prop]
    k.state.actors = {"player": actor}
    k._write_turn_state(current_events=[])
    portfolio = bus.state["player_state"]["portfolio"]
    assert len(portfolio) == 1
    assert portfolio[0]["renovated"] is False
