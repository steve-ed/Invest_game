"""Tally per-actor podium stats across N games — fast headless runner."""
import collections
import os
import sys

# Minimal player engine — no file I/O, no logging
class _QuietPlayer:
    """Replicates ClaudePlayerEngine logic without any file writes or prints."""
    BUY_LTV          = 0.75
    CASH_RESERVE     = 150_000
    SELL_LTV         = 0.80
    HIGH_RATE        = 0.065
    EPC_COST         = {4: 5_000, 5: 12_000, 6: 20_000, 7: 30_000}
    EPC_RESERVE      = 2.0

    def __init__(self):
        self.start_cash = None
        self.start_portfolio_value = None

    def step(self, state, tick):
        if self.start_cash is None:
            actor = state.actors.get("player")
            if actor:
                self.start_cash = actor.cash
                prop_map = {p.id: p for p in state.properties}
                self.start_portfolio_value = sum(
                    prop_map[pid].current_value for pid in actor.portfolio if pid in prop_map
                )
        actor = state.actors.get("player")
        if not actor:
            return [{"type":"player_action","tick":tick,"actor_id":"player","action":"hold","property_id":None,"ltv":0.0,"detail":"hold"}]
        action, pid, ltv = self._decide(state, actor)
        return [{"type":"player_action","tick":tick,"actor_id":"player","action":action,"property_id":pid,"ltv":ltv,"detail":f"Player:{action}"}]

    def _decide(self, state, actor):
        from void_maintenance import expected_maintenance_reserve
        prop_map  = {p.id: p for p in state.properties}
        held      = [prop_map[pid] for pid in actor.portfolio if pid in prop_map]
        owned_all = {pid for a in state.actors.values() for pid in a.portfolio}
        available = [p for p in state.properties if p.id not in owned_all]
        rate      = state.macro.interest_rate

        for prop in held:
            if prop.fixed_ticks_remaining == 0 and prop.mortgage_balance > 0:
                if max(0.0, prop.current_value * 0.75 - prop.mortgage_balance) >= 20_000:
                    return "refi", prop.id, 0.0

        for pid, prop in sorted(
            [(pid, prop_map[pid]) for pid in actor.portfolio
             if pid in prop_map and prop_map[pid].epc_band >= 4],
            key=lambda x: -x[1].epc_band,
        ):
            cost = self.EPC_COST.get(prop.epc_band, 0)
            if cost and actor.cash >= cost * self.EPC_RESERVE:
                return "upgrade", pid, 0.0

        if rate > self.HIGH_RATE:
            for prop in sorted(held, key=lambda p: -(p.mortgage_balance / p.current_value if p.current_value else 0)):
                if (prop.mortgage_balance / prop.current_value if prop.current_value else 0) > self.SELL_LTV:
                    return "sell", prop.id, 0.0

        if rate <= self.HIGH_RATE:
            for prop in sorted(available, key=lambda p: -(p.rent * 12) / p.current_value):
                if (prop.rent * 12) / prop.current_value < 0.055:
                    continue
                deposit = prop.current_value * (1 - self.BUY_LTV)
                sdlt    = _sdlt(prop.current_value)
                reserve = expected_maintenance_reserve(prop)
                if actor.cash >= deposit + sdlt + self.CASH_RESERVE + reserve:
                    return "buy", prop.id, self.BUY_LTV

        return "hold", None, 0.0


def _sdlt(price):
    bands = [(125_000,0.0),(250_000,0.02),(925_000,0.05),(1_500_000,0.10),(float("inf"),0.12)]
    tax, prev = 0.0, 0.0
    for threshold, rate in bands:
        if price <= prev: break
        tax  += (min(price, threshold) - prev) * rate
        prev  = threshold
    return tax


# Patch kernel to skip file I/O for ready/action signals
import kernel as km
from kernel import SimulationKernel, READY_PATH

os.makedirs(os.path.dirname(READY_PATH), exist_ok=True)
_orig_exists = km.os.path.exists
_orig_remove = km.os.remove
_ready_norm  = os.path.normcase(READY_PATH)
km.os.path.exists = lambda p: True if os.path.normcase(p) == _ready_norm else _orig_exists(p)
km.os.remove      = lambda p: None if os.path.normcase(p) == _ready_norm else _orig_remove(p)
km.time.sleep     = lambda _: None

GAMES = 99

appeared = collections.Counter()
wins     = collections.Counter()
seconds  = collections.Counter()
thirds   = collections.Counter()
scores   = collections.defaultdict(list)
equities = collections.defaultdict(list)
cashes   = collections.defaultdict(list)
void_l   = collections.defaultdict(list)
maint_c  = collections.defaultdict(list)

# per-game records for correlation analysis: (player_start_cash, player_won)
cash_win_records = []

for g in range(1, GAMES + 1):
    qp = _QuietPlayer()
    k = SimulationKernel(turns=20, mode="student", turn_delay=0)
    k.player_choices = qp
    results = k.run()
    lb = results["leaderboard"]

    for rank, entry in enumerate(lb, 1):
        name = entry["name"]
        appeared[name] += 1
        if rank == 1: wins[name]    += 1
        if rank == 2: seconds[name] += 1
        if rank == 3: thirds[name]  += 1
        scores[name].append(entry["final_score"])
        equities[name].append(entry["portfolio_value"])
        cashes[name].append(entry["cash"])
        if name == "You" and qp.start_portfolio_value is not None:
            cash_win_records.append((qp.start_portfolio_value, rank == 1))
    for actor in k.state.actors.values():
        void_l[actor.name].append(actor.total_void_losses)
        maint_c[actor.name].append(actor.total_maintenance_costs)
    if g % 10 == 0:
        print(f"  {g}/{GAMES} done", flush=True)

print(f"\nPodium Distribution — {GAMES} games")
print(f"{'Actor':<24} {'App':>4} {'1st':>4} {'2nd':>4} {'3rd':>4} {'Win%':>6} {'AvgScore':>12} {'AvgEquity':>12} {'AvgCash':>12}")
print("-" * 96)
for name in sorted(appeared, key=lambda n: -wins[n]):
    app  = appeared[name]
    w    = wins[name]
    wpct = w / app * 100
    asc  = sum(scores[name])   / len(scores[name])
    aeq  = sum(equities[name]) / len(equities[name])
    aca  = sum(cashes[name])   / len(cashes[name])
    print(f"{name:<24} {app:>4} {w:>4} {seconds[name]:>4} {thirds[name]:>4} {wpct:>5.1f}% £{asc:>10,.0f} £{aeq:>10,.0f} £{aca:>10,.0f}")

print(f"\nVoid & Maintenance drag (avg per game)")
print(f"{'Actor':<24} {'AvgVoidLoss':>14} {'AvgMaintCost':>14}")
print("-" * 56)
for name in sorted(appeared, key=lambda n: -wins[n]):
    if void_l[name]:
        print(f"{name:<24} £{sum(void_l[name])/len(void_l[name]):>12,.0f} £{sum(maint_c[name])/len(maint_c[name]):>12,.0f}")

# ── Starting cash vs win correlation ────────────────────────────────────────
print(f"\nPlayer Starting Portfolio Value vs Win Rate")
print("-" * 50)
buckets = [(0, 300_000), (300_000, 400_000), (400_000, 500_000), (500_000, 600_000), (600_000, float("inf"))]
for lo, hi in buckets:
    subset = [(c, w) for c, w in cash_win_records if lo <= c < hi]
    if not subset: continue
    win_rate = sum(w for _, w in subset) / len(subset) * 100
    label = f"£{lo//1000}k–£{hi//1000 if hi != float('inf') else 'over'}k"
    print(f"  {label:<16} n={len(subset):>3}  win%={win_rate:>5.1f}%")

# Pearson correlation: cash vs win (1/0)
xs = [c for c, _ in cash_win_records]
ys = [1 if w else 0 for _, w in cash_win_records]
n  = len(xs)
mx, my = sum(xs)/n, sum(ys)/n
cov = sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / n
sx  = (sum((x-mx)**2 for x in xs)/n)**0.5
sy  = (sum((y-my)**2 for y in ys)/n)**0.5
r   = cov/(sx*sy) if sx and sy else 0
print(f"\n  Pearson r (cash vs win): {r:+.3f}  ({'positive' if r>0.05 else 'negative' if r<-0.05 else 'no'} correlation)")
