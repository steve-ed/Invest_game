"""Run N games headlessly and report advice distribution from _player_eval."""
import collections
import os
import sys

READY_PATH  = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
ACTION_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "player_action.json")

import kernel as kernel_module
from kernel import SimulationKernel
from claude_player import ClaudePlayerEngine, _patch_kernel

os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)
_patch_kernel(kernel_module)

GAMES = 20

advice_tally   = collections.Counter()
strategy_tally = collections.Counter()
combo_tally    = collections.Counter()

for g in range(1, GAMES + 1):
    k = SimulationKernel(turns=20, mode="student", turn_delay=0)
    k.player_choices = ClaudePlayerEngine()
    k.run()
    for entry in k._player_eval:
        adv   = entry.get("advice", "hold").split()[0]
        strat = entry.get("adv_strategy", "balanced")
        p_act = entry.get("player", "hold").split()[0]
        advice_tally[adv]       += 1
        strategy_tally[strat]   += 1
        combo_tally[(p_act, adv)] += 1
    print(f"Game {g:>2} done", flush=True)

total = sum(advice_tally.values())
print(f"\nAdvice distribution ({total} ticks, {GAMES} games):")
for act, n in advice_tally.most_common():
    print(f"  {act:<10} {n:>4}  ({n/total:.0%})")

print("\nStrategy selected by advice engine:")
for s, n in strategy_tally.most_common():
    print(f"  {s:<12} {n:>4}  ({n/total:.0%})")

print("\nPlayer action vs Advice (top combos):")
for (p, a), n in combo_tally.most_common(15):
    agree = " *" if p == a else ""
    print(f"  player={p:<10} advice={a:<10} {n:>4}{agree}")
