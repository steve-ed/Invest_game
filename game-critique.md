# Strategy Critique: Real-World Intent vs Game Implementation

Generated: 2026-07-19 | Based on 99-game simulation data

---

## Context

Each AI actor embodies a recognised UK property investment archetype. This document reviews how faithfully each strategy is implemented against its real-world counterpart, and identifies anomalies that distort game outcomes or teaching value.

Win rates from 99-game baseline (post value-add fix):

| Actor | Strategy | Appearances | Wins | Win/game% |
|---|---|---|---|---|
| Mr Hugh Price | capital | 32 | 24 | 75.0% |
| Mr Ray Novate | value_add | 42 | 20 | 47.6% |
| Ms Demi Graphic | demographic | 29 | 12 | 41.4% |
| Mr Max Lever | leverage | 31 | 8 | 25.8% |
| Ms Di Vidend | yield | 35 | 5 | 14.3% |
| Mr Reid Furbish | brrr | 29 | 3 | 10.3% |

---

## 1. Yield — Ms Di Vidend

### Real-world intent

High-income landlord. Targets 6–8%+ gross yield Northern/Midlands properties. Uses moderate leverage (60–70% LTV) to amplify cash-on-cash return. Core metric is positive monthly cash flow after all costs. Holds long term; does not speculate on capital growth.

### Game implementation

Rate-gated buyer at 35% LTV, 5% net yield minimum. Never sells, refis, upgrades or renovates.

### Anomalies

**35% LTV is too conservative by a factor of two.** At 35% LTV on a £130k Sheffield property the deposit is £84.5k. Real yield investors use 65–70% LTV to make their capital work — amplified cash-on-cash return is the entire rationale of leveraged buy-to-let income. At 35%, Di Vidend's return on capital deployed barely exceeds savings interest, and her cash pile sits idle for most of the game.

**Starting portfolio contradicts the strategy.** p04 (Sheffield EPC E, value_add archetype) and p05 (Leicester EPC E, value_add archetype) are distressed, void-prone stock. A yield investor would start with stable, already-tenanted BTL properties in good condition. These are Ray Novate's natural territory, not Di Vidend's.

**Never upgrades EPC.** p04 and p05 are EPC E (band 5), which carries a 15% scoring penalty at game end. Di Vidend holds non-compliant stock indefinitely, taking a material score hit for properties she could upgrade for £8k each.

**No sell trigger.** In practice, yield investors exit when price appreciation has compressed the gross yield below their threshold — the property has become a capital asset, not an income asset. No exit logic means Di Vidend holds forever regardless of whether the yield rationale still holds.

**Severity: High** — the LTV error and wrong starting properties structurally undermine the strategy.

---

## 2. Leverage — Mr Max Lever

### Real-world intent

Maximum leverage BTL. Buys at 75% LTV in rising markets to maximise return on equity. Accepts low or negative cash flow because capital appreciation covers it. Exits when rate spikes threaten cash flow. Classic 2000s–2010s investor profile.

### Game implementation

75% LTV, buys when rate ≤ 6.5%, sells highest-LTV property when rate > 8.5%.

### Anomalies

**Never refis.** Real leverage investors refinance every 2–3 years as fixed terms expire, pulling out accumulated equity to fund the next purchase. This is their core scaling mechanism. Max Lever builds equity and leaves it locked in. Without refi, the strategy cannot compound.

**Sell threshold (8.5%) is too high.** At 75% LTV with a 2.2% mortgage spread, Max is already paying 8.7% on his mortgages when BoE = 6.5% — his buy gate. At the 8.5% sell gate, he is paying 10.7%. A 75% LTV landlord at 10.7% mortgage rate is deeply cash-flow negative on all properties simultaneously. The sell trigger should be closer to 7.5–8.0%.

**Sell decision ignores cash-flow fundamentals.** Max sells the highest-LTV property, which is geometrically correct for stress reduction but ignores which property has the worst ICR. A real investor sells the property with the worst cash flow first — highest interest relative to rent — which may not be the highest-LTV property.

**Concentration risk unmanaged.** Max buys the first affordable property regardless of region, accumulating concentration risk and the associated scoring penalty. Real leveraged investors spread geographically precisely because their high LTV amplifies any regional downturn.

**Severity: Medium** — wins when present in boom eras, but the missing refi and wrong sell threshold limit scalability.

---

## 3. Capital Growth — Mr Hugh Price

### Real-world intent

Long-hold capital appreciation. Target £200k+ South and East of England properties in strong-HPI corridors. Low LTV (40–55%) to safely hold through full cycles. Sell into downturns; reinvest at the trough. Yield is secondary; the game is time in market.

### Game implementation

50% LTV, £150k minimum value filter, sells after 2 consecutive price-index falls. Never refis or renovates.

### Anomalies

**Never refis.** Capital growth investors extract equity after material appreciation (a 20–30% rise creates substantial headroom at 50% LTV). Hugh accumulates appreciation but never deploys it. Equity recycling into further purchases is how the strategy compounds, and it is completely absent.

**No regional targeting.** The £150k value filter catches mid-value stock but does not specifically target London (HPI factor 1.35) or South (1.15) where appreciation is structurally strongest. Hugh may end up with Sheffield or Newcastle properties (HPI 0.85) simply because they exceed £150k after appreciation. A true capital growth strategy should rank by region HPI factor, not just purchase price.

**Sell condition is reactive, not anticipatory.** Waiting for two consecutive falls means Hugh sells after the market has already dropped. Capital growth investors in practice sell on macro signals — rate spikes, credit conditions — before falls materialise, preserving more of the gain.

**Starting portfolio (p06 Bristol, p07 Cambridge)** is genuinely appropriate: South/East markets, EPC C, quality stock. No issue here.

**Severity: Medium** — the missing refi is a significant gap; regional blindness is correctable by sorting candidates by HPI region profile.

---

## 4. BRRR — Mr Reid Furbish

### Real-world intent

Buy-Refurbish-Refinance-Rent-Repeat. The defining feature is a full refurb — kitchen, bathroom, sometimes structural work — that transforms a distressed property into rentable stock at a higher value. Refinance at 75% LTV post-works pulls out all or most of the invested capital. Repeat indefinitely with recycled money.

### Game implementation

EPC upgrades only, 75% LTV refi, hard portfolio cap of 4, complex conditional refi logic.

### Anomalies

**Never uses the renovate action.** This is a fundamental implementation gap. The strategy is named after refurbishment. The game's `renovate` action (10% cost, +8% value, +15% rent uplift) is exactly the full refurb that justifies the BRRR refi. Reid Furbish only does EPC compliance work. Without renovation, the post-works value uplift is limited to EPC band improvement (6–18%), whereas stacking renovation adds a further 8% value and 15% rent — directly increasing the equity available to refi out. Value-add was fixed to stack both actions; BRRR should be at least as strong.

**Mortgage spread inconsistency.** The BRRR cash-flow gate uses `rate + 0.018` but the actual kernel mortgage rate is `rate + 0.022`. At 5% BoE: the AI models a 6.8% mortgage while the lender charges 7.2%. On a £150k mortgage this is a £600/year underestimate. The strategy will occasionally buy properties it considers cash-flow positive that the lender's ICR check then rejects — causing silent failed buys identical to the issue value-add had before the fix.

**Portfolio cap of 4 is artificial.** In practice there is no ceiling on BRRR — the recycled capital model is designed for unlimited repetition. The cap introduces a forced-sell mechanism (sell worst performer when at capacity) that has no real-world equivalent and distorts strategy behaviour in the mid-game.

**Refi is over-gated.** BRRR only refis when portfolio ≥ 4 OR (rate ≤ 7% AND a buy candidate exists). A real BRRR investor refis as soon as works are complete and the fixed term expires, regardless of whether a next purchase is immediately lined up. The refi IS the strategy — it should not be conditional on portfolio size or available stock.

**Starting portfolio (p10 Leeds EPC E, p11 Nottingham HMO EPC E)** — appropriate for BRRR. Both distressed, both upgradeable.

**Severity: High** — the missing renovate action is structurally identical to the value-add bug that produced 0 wins in 99 games.

---

## 5. Demographic — Ms Demi Graphic

### Real-world intent

Demand-led rental investor. Buys in areas with structurally strong population growth, university towns, commuter corridors, and regeneration zones where tenant demand and rent growth are above-average long-term. Exits when fundamentals weaken.

### Game implementation

50% LTV, follows national rent_growth index, regional sort logic, sells on 3 consecutive ticks of negative rent growth.

### Anomalies

**Sell logic picks `actor.portfolio[0]`** — the first item in the portfolio list, which is effectively arbitrary. A demographic investor who is selling because rent growth has turned negative should sell the property in the weakest-demand region, or the one with the lowest yield, or the highest concentration. The first-in-list behaviour has no economic rationale and will sometimes sell the best property in the portfolio.

**National rent_growth index masks local signals.** The sell trigger uses a single macro index. A real demographic investor tracks city-level or postcode-level demand. Using one national figure means all demographic actors respond at exactly the same moment to exactly the same signal — there is no differentiation between a Manchester landlord and a Sunderland landlord reacting to demographic shifts.

**Starting portfolio (p14 Newcastle EPC E, p15 Sunderland EPC E)** — both are low-growth Northern markets. p15 Sunderland (£90k) is below the value_add minimum and has a North HPI factor of 0.85. A demographic investor should start in more demographically active locations — Manchester, Bristol, Leeds — not in structurally declining post-industrial cities. Both carry EPC scoring penalties the strategy never addresses.

**Regional sort intent is unclear.** The sort key `(p.region in held_regions, -p.rent / p.current_value)` ranks properties in NEW regions before existing ones. This diversifies away from concentration (a scoring benefit) but runs counter to the local-expertise rationale that makes demographic investing effective. If the intent is geographic diversification, the strategy name and actor profile should reflect that; if it is local expertise, the sort should be reversed.

**Never upgrades or renovates.** A landlord targeting quality tenants in high-demand areas would maintain and improve properties to attract and retain them. Ms Graphic's non-compliant starting stock (EPC E) takes the full 15% scoring penalty.

**Severity: Medium** — the sell logic and starting portfolio are the clearest correctable gaps.

---

## 6. Value-Add — Mr Ray Novate *(post-fix, July 2026)*

### Real-world intent

BRRR variant focused on energy-efficiency uplift and cosmetic refurbishment. Buy distressed EPC E/F/G properties at a discount, upgrade to EPC C compliance, renovate, refi at improved value, repeat. Faster cycle than heavy-refurb BRRR; targets Northern/Midlands stock where distress discounts are deepest.

### Game implementation (post-fix)

ICR-constrained buy LTV, EPC upgrade → renovate → refi at 75% LTV, rate-gated buying, sell non-compliant high-LTV stock at rate spikes.

### Remaining anomalies

**No auction bid premium.** Ray bids at 0% on auction lots. Real value-add investors compete aggressively at auction because the distressed discount is their structural edge — they will pay 3–5% above estimate if the deal still stacks post-works. Allowing Ray a small bid premium on distressed auction lots would better reflect how these investors operate.

**Buy rate gate (7.5%) is slightly high for a bridging-style buyer.** In practice, value-add acquisitions are funded on short-term bridge finance (typically BoE + 5–6%) which is available regardless of BoE rate. The rate gate makes sense for the BTL refi, but the acquisition itself should be rate-agnostic — the investor buys when the deal works, not when BoE cooperates.

**Severity: Low** — the strategy now correctly implements the full cycle and wins competitively.

---

## Priority Fix List

| Priority | Fix | Strategy | Expected impact |
|---|---|---|---|
| 1 | Add renovate action to BRRR | brrr | Likely to replicate value-add improvement from 10% → 40%+ win rate |
| 2 | Raise yield LTV from 35% to ~65% | yield | Di Vidend's cash will work significantly harder |
| 3 | Fix BRRR mortgage spread (0.018 → 0.022) | brrr | Removes silent failed buys |
| 4 | Add refi to capital growth | capital | Equity recycling enables further purchases in long booms |
| 5 | Add regional HPI targeting to capital | capital | Directs Hugh to 1.15–1.35× HPI regions |
| 6 | Fix demographic sell (portfolio[0] → worst performer) | demographic | Economically rational exit |
| 7 | Fix yield starting portfolio (p04/p05 → stable BTL) | yield | Removes EPC penalty from a strategy that never upgrades |
| 8 | Lower leverage sell gate (8.5% → ~7.5%) | leverage | Earlier exit before deep cash-flow distress |
| 9 | Add refi to leverage | leverage | Core equity recycling mechanism |
| 10 | Remove BRRR portfolio cap or raise to 6+ | brrr | Reflects unlimited-repeat nature of the strategy |
