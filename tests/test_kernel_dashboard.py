from kernel import SimulationKernel


def test_macro_history_grows_one_per_tick():
    kernel = SimulationKernel(turns=3, turn_delay=0)
    kernel.run()
    assert len(kernel.state.macro_history) == 3


def test_macro_snapshot_tick_values():
    kernel = SimulationKernel(turns=2, turn_delay=0)
    kernel.run()
    assert kernel.state.macro_history[0].tick == 1
    assert kernel.state.macro_history[1].tick == 2


def test_macro_snapshot_records_scenario():
    kernel = SimulationKernel(turns=1, turn_delay=0)
    kernel.run()
    snap = kernel.state.macro_history[0]
    assert isinstance(snap.scenario, str)
    assert len(snap.scenario) > 0


def test_state_event_log_accumulates_events():
    kernel = SimulationKernel(turns=3, turn_delay=0)
    kernel.run()
    assert len(kernel.state.event_log) > 0


def test_last_ai_actions_populated_after_run():
    kernel = SimulationKernel(turns=1, turn_delay=0)
    kernel.run()
    assert "ai1" in kernel.state.last_ai_actions
    assert "ai2" in kernel.state.last_ai_actions


def test_last_ai_actions_values_are_strings():
    kernel = SimulationKernel(turns=1, turn_delay=0)
    kernel.run()
    for actor_id in ("ai1", "ai2"):
        val = kernel.state.last_ai_actions.get(actor_id)
        assert isinstance(val, str)
        assert len(val) > 0
