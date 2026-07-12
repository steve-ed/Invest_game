import matplotlib.pyplot as plt


def plot_shock_timeline(trace):
    ticks = []
    labels = []
    for entry in trace:
        for event in entry["events"]:
            if event["type"] == "shock":
                ticks.append(entry["tick"])
                labels.append(event.get("shock_type", "shock"))

    all_ticks = [e["tick"] for e in trace]
    fig, ax = plt.subplots(figsize=(10, 3))
    for i, (tick, label) in enumerate(zip(ticks, labels)):
        ax.axvline(x=tick, color="red", linestyle="--", alpha=0.7)
        ax.text(tick + 0.1, 0.5 + (i % 2) * 0.3, label, rotation=45, fontsize=8, color="red")

    if all_ticks:
        ax.set_xlim(min(all_ticks) - 0.5, max(all_ticks) + 0.5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Tick")
    ax.set_title("Shock Timeline")
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig("shock_timeline.png")
    plt.close()
    print("Saved shock_timeline.png")
