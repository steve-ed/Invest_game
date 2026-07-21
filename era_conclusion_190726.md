# Era Analysis — Conclusions (19 July 2026)

## Method

30 pinned games per start year, 1984–2014 (31 years × 30 games = 930 games total).
Each game randomises start half (H1/H2) and AI actor roster. Win/game% = wins ÷ appearances
(appearances-adjusted, since roster is randomised and not every strategy appears in every game).

---

## Results Summary

| Year | Best Strategy | Win% | Capital | Demographic | Leverage | BRRR | Value-Add | Yield |
|------|--------------|-------|---------|-------------|----------|------|-----------|-------|
| 1984 | Capital Growth | 62% | 62% | 0% | 18% | 9% | 50% | 57% |
| 1985 | Value-Add | 71% | 57% | 20% | 0% | 33% | 71% | 20% |
| 1986 | Capital Growth | 67% | 67% | 50% | 20% | 8% | 29% | 67% |
| 1987 | Yield | 100% | 60% | 20% | 27% | 20% | 57% | 100% |
| 1988 | Capital Growth | 88% | 88% | 38% | 67% | 0% | 36% | 53% |
| 1989 | Yield | 70% | 67% | 17% | 67% | 17% | 27% | 70% |
| 1990 | Demographic | 67% | 29% | 67% | 18% | 18% | 29% | 42% |
| 1991 | Demographic | 73% | 0% | 73% | 0% | 25% | 7% | 50% |
| 1992 | Value-Add | 50% | 18% | 43% | 0% | 12% | 50% | 25% |
| 1993 | BRRR | 30% | 9% | 18% | 0% | 30% | 30% | 14% |
| 1994 | Value-Add | 78% | 0% | 20% | 0% | 38% | 78% | 0% |
| 1995 | BRRR | 83% | 11% | 12% | 0% | 83% | 27% | 44% |
| 1996 | Value-Add | 64% | 0% | 17% | 0% | 60% | 64% | 33% |
| 1997 | Demographic | 46% | 0% | 46% | 0% | 15% | 25% | 40% |
| 1998 | BRRR | 56% | 0% | 40% | 0% | 56% | 11% | 38% |
| 1999 | BRRR | 50% | 0% | 20% | 0% | 50% | 27% | 22% |
| 2000 | Demographic | 75% | 14% | 75% | 57% | 55% | 27% | 12% |
| 2001 | Capital Growth | 100% | 100% | 50% | 83% | 25% | 9% | 0% |
| 2002 | Capital Growth | 89% | 89% | 40% | 62% | 18% | 0% | 0% |
| 2003 | Capital Growth | 100% | 100% | 40% | 55% | 17% | 10% | 25% |
| 2004 | Capital Growth | 89% | 89% | 33% | 73% | 0% | 9% | 0% |
| 2005 | Capital Growth | 100% | 100% | 50% | 73% | 0% | 10% | 0% |
| 2006 | Leverage | 78% | 75% | 33% | 78% | 13% | 0% | 10% |
| 2007 | Capital Growth | 88% | 88% | 33% | 78% | 0% | 0% | 29% |
| 2008 | Capital Growth | 100% | 100% | 60% | 50% | 0% | 0% | 0% |
| 2009 | Capital Growth | 100% | 100% | 60% | 45% | 9% | 0% | 0% |
| 2010 | Capital Growth | 100% | 100% | 80% | 75% | 29% | 0% | 0% |
| 2011 | Capital Growth | 100% | 100% | 50% | 71% | 25% | 11% | 0% |
| 2012 | Capital Growth | 100% | 100% | 67% | 73% | 54% | 20% | 0% |
| 2013 | Capital Growth | 100% | 100% | 60% | 86% | 40% | 8% | 0% |
| 2014 | Capital Growth | 100% | 100% | 75% | 75% | 25% | 14% | 0% |

---

## Structural Patterns

### 1984–2000: Diverse era, strategy matters
No single strategy dominates. The right play depends heavily on the macro cycle:
- Capital Growth wins in recovery and early-boom starts (1984, 1986, 1988)
- Yield wins at the peak of the boom (1987, 1989) where income cover matters most
- Demographic wins in the crash and stagnation years (1990, 1991, 1997, 2000)
- BRRR and Value-Add dominate the mid-90s recovery (1993–1999) — the BTL mortgage era

### 2001–2014: Capital Growth era, leverage amplifies
From 2001 onwards Capital Growth wins at 100% for most start years. Leverage is a strong second
(83% in 2001, 73–86% in 2004–2013) — it benefits from the same price surge and is consistently
the second-best strategy. The era is so one-directional that income-focused strategies score 0%.

### The one exception: 2006
Leverage edges Capital Growth 78% vs 75%. The peak credit cycle (2004–07) is the one moment
where maximum LTV outperforms pure accumulation — catching the last of the pre-GFC price surge
before rates turned.

---

## Impact on Debrief Narrative Guidance

The current `era_narratives.py` file contains an `optimal` field shown to players on the debrief
page. Several entries diverge meaningfully from what the simulation rewards:

| Era narrative label | Current `optimal` field | What the simulation shows |
|---|---|---|
| Early Thatcher Recovery (1984 start) | "Yield strategy: buy income-generating properties as rates eased" | Capital Growth wins 62%, Yield 57% — close but Capital edges it |
| Late Thatcher Boom (1987 start) | "Capital growth early in the era" | Yield wins at **100%** — the single strongest era result in the dataset |
| Mid-Nineties Recovery (1993–96) | "Yield strategy with moderate leverage" | BRRR wins 83% (1995), Value-Add wins 78% (1994) — Yield barely registers |
| GFC & Austerity (2008–09) | "Income-first before the crash. Hold through the fall." | Capital Growth wins **100%** in both years |
| Post-GFC Long Recovery (2010+) | "Yield strategy with company structure" | Capital Growth wins **100%** for every start year 2008–2014 |

### Educational risk

The debrief tells players what the optimal strategy was — and then they play again. If the
narrative says "yield" in an era where the game rewards capital growth at 100%, players who
follow that advice will lose and be confused. The narrative and the game mechanics contradict
each other.

### Options

**Option 1 — Update `optimal` to match the simulation**
Replace narrative `optimal` fields with the strategy the game actually rewards in each era.
Makes debrief self-consistent with game outcomes. Cleaner UX.

**Option 2 — Separate historical truth from game model**
Keep the historical narrative as written (reflecting real-world strategy) but add a second line
such as "In this simulation, Capital Growth dominated — the game's simplified price model
rewards accumulation more than income in sustained boom periods."
More honest educationally; acknowledges the game is a model, not reality.

### Recommendation

Option 2 for the four mismatched eras. The narratives reflect genuinely important real-world
lessons (income cover before a crash, yield focus in uncertain periods) that should not be
discarded. Adding a "What won in the simulation" line preserves the lesson while making the
debrief consistent with what the player just experienced.
