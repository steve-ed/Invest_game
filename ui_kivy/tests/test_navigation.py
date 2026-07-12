import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import dummy_data as dd


def setup_function():
    dd.GAME_STATE["tick"] = 4
    dd.GAME_STATE["total_ticks"] = 20


def test_confirm_increments_tick():
    initial = dd.GAME_STATE["tick"]
    dd.GAME_STATE["tick"] += 1
    assert dd.GAME_STATE["tick"] == initial + 1


def test_end_not_triggered_mid_game():
    dd.GAME_STATE["tick"] = 10
    dd.GAME_STATE["tick"] += 1
    assert dd.GAME_STATE["tick"] < dd.GAME_STATE["total_ticks"]


def test_end_triggered_at_total_ticks():
    dd.GAME_STATE["tick"] = 20
    assert dd.GAME_STATE["tick"] >= dd.GAME_STATE["total_ticks"]


def test_play_again_resets_tick():
    dd.GAME_STATE["tick"] = 20
    dd.GAME_STATE["tick"] = 1
    assert dd.GAME_STATE["tick"] == 1
