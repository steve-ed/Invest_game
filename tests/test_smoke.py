from kernel import SimulationKernel


def test_full_20_turn_game_completes():
    kernel = SimulationKernel(turns=20, turn_delay=0)
    results = kernel.run()
    assert len(results["trace"]) == 20
    assert len(results["leaderboard"]) == 3
    assert len(kernel.state.macro_history) == 20


def test_leaderboard_contains_all_actors():
    kernel = SimulationKernel(turns=20, turn_delay=0)
    results = kernel.run()
    names = {e["name"] for e in results["leaderboard"]}
    assert "Player" in names
    assert "Conservative AI" in names
    assert "Aggressive AI" in names


def test_event_log_has_events():
    kernel = SimulationKernel(turns=20, turn_delay=0)
    kernel.run()
    assert len(kernel.state.event_log) > 0


def test_macro_history_price_index_populated():
    kernel = SimulationKernel(turns=20, turn_delay=0)
    kernel.run()
    assert all(s.price_index > 0 for s in kernel.state.macro_history)
