# UI Readability & AI Panel Enrichment — Design Spec

Date: 2026-06-30

## Problem

1. All text in the Kivy UI uses `7sp`–`10sp` fonts, which are unreadable at typical desktop window sizes.
2. The AI Positions panel on the Turn screen shows only a single word (`last_action`), giving no insight into what each AI actually did or why.

## Scope

Files touched: `ui_kivy/dummy_data.py`, `ui_kivy/widgets/macro_sidebar.kv`, `ui_kivy/screens/turn.kv`, `ui_kivy/screens/turn.py`, `ui_kivy/screens/decision.kv`, `ui_kivy/screens/decision.py`.

No new screens, no new widgets, no backend changes.

---

## Design

### 1. Font & Layout Scaling

Widen the `MacroSidebar` from `90dp` to `130dp` to accommodate larger text without wrapping.

Font size changes (old → new):

| Location | Element | Old | New |
|---|---|---|---|
| `macro_sidebar.kv` | Section labels (TICK, RANK, etc.) | `7sp`–`8sp` | `11sp` |
| `macro_sidebar.kv` | Tick number | `22sp` | `28sp` |
| `macro_sidebar.kv` | Macro values (price index, rate) | `10sp` | `14sp` |
| `macro_sidebar.kv` | Scenario name | `9sp` | `13sp` |
| `macro_sidebar.kv` | Rank number | `18sp` | `22sp` |
| `macro_sidebar.kv` | Score / cash values | `9sp`–`11sp` | `13sp` |
| `turn.kv` | Panel section labels | `8sp` | `12sp` |
| `turn.py` | Portfolio grid cells | `9sp` | `12sp` |
| `turn.py` | Portfolio grid row height | `18dp` | `24dp` |
| `turn.py` | News items | `9sp` | `12sp` |
| `turn.py` | News item height | `18dp` | `22dp` |
| `decision.kv` | Panel section labels | `8sp` | `12sp` |
| `decision.kv` | Action buttons | `14sp` | `18sp` |
| `decision.py` | Market property rows | `9sp` | `12sp` |
| `decision.py` | Market row height | `28dp` | `36dp` |

The AI panel rows in `turn.py` are handled separately under Section 2 below.

---

### 2. AI Panel Enrichment

#### Data layer (`dummy_data.py`)

Each AI entry in `GAME_STATE["ai"]` gains two fields:

```python
{
    "name": "Aggressive",
    "cash": 15000,
    "portfolio_value": 520000,
    "props": 4,
    "last_action": "buy",
    "last_property": "P-003",      # property ID acted on; None for hold
    "rationale": "chasing yield in North"  # short human-readable string
}
```

#### Display (`turn.py` + `turn.kv`)

Replace the flat 4-column `GridLayout` in the AI panel with a vertical `BoxLayout` of per-AI blocks built in Python.

Each AI block is a `BoxLayout` (vertical, `size_hint_y: None`, height `44dp`) containing two `Label` rows:

- **Line 1** — `[AI NAME]   £520,000   4 props`
  - Name colored by strategy: yellow for Conservative, red for Aggressive
  - Value and prop count in muted body color
  - `font_size: 12sp`

- **Line 2** — `→ bought P-003 · chasing yield in North`
  - Action verb colored: green (`#00FF88`) for buy, red for sell, muted for hold
  - Rationale in dim color
  - `font_size: 11sp`

Action verb mapping:
- `buy` → `"bought {last_property}"`
- `sell` → `"sold {last_property}"`
- `hold` → `"held"`

#### Layout adjustment

The AI panel `size_hint_y` stays at `0.22` but the inner blocks now use `44dp` each. With 2 AIs that is `88dp` total, which fits comfortably within a typical window height.

Remove the `ai_grid` `GridLayout` id from `turn.kv`; replace with a plain `BoxLayout` id `ai_box`.

---

## What is not changing

- Screen navigation logic
- Macro sidebar behaviour or properties exposed
- Opening and End screens (no dense text)
- Game state structure beyond the two new AI fields
