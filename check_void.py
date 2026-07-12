import os, sys, collections
READY_PATH = os.path.join(os.path.dirname(__file__), "visualisation", "ready.json")
os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)
import kernel as km
from kernel import SimulationKernel
from claude_player import ClaudePlayerEngine, _patch_kernel
_patch_kernel(km)

k = SimulationKernel(turns=20, mode="student", turn_delay=0)
k.player_choices = ClaudePlayerEngine()
k.run()

void_events  = [e for e in k.state.event_log if e["type"] == "void_period"]
maint_events = [e for e in k.state.event_log if e["type"] == "maintenance"]
print(f"\nVoid events: {len(void_events)}")
for e in void_events[:8]:
    print(f"  tick {e['tick']}  {e['detail']}")
print(f"\nMaintenance events: {len(maint_events)}")
for e in maint_events[:8]:
    print(f"  tick {e['tick']}  {e['detail']}")
print()
for aid, actor in k.state.actors.items():
    print(f"{actor.name:<22}  void_losses=£{actor.total_void_losses:>8,.0f}  maint=£{actor.total_maintenance_costs:>8,.0f}")
