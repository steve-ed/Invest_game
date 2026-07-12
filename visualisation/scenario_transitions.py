import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

SCENARIO_COLOURS = {
    "baseline": "#209dd7",
    "downturn": "#c0392b",
    "recovery": "#27ae60",
}


def plot_scenario_transitions(trace):
    scenario_by_tick = {}
    for entry in trace:
        for event in entry["events"]:
            if event["type"] in ("scenario_advance", "scenario_transition"):
                scenario_by_tick[entry["tick"]] = event.get("scenario", "baseline")

    all_ticks = [e["tick"] for e in trace]
    fig, ax = plt.subplots(figsize=(10, 2))
    for tick in all_ticks:
        scenario = scenario_by_tick.get(tick, "baseline")
        colour = SCENARIO_COLOURS.get(scenario, "#888888")
        ax.barh(0, 1, left=tick - 1, height=0.8, color=colour, align="edge")

    patches = [mpatches.Patch(color=c, label=s) for s, c in SCENARIO_COLOURS.items()]
    ax.legend(handles=patches, loc="upper right")
    ax.set_xlabel("Tick")
    ax.set_title("Scenario Transitions")
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig("scenario_transitions.png")
    plt.close()
    print("Saved scenario_transitions.png")
