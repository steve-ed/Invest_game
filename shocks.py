# Each rule: (event_type, condition_fn(rate_delta, hpi_delta_pct, rent_delta), detail_str, delta_key)
# rate_delta: percentage points (e.g. +1.5 means rate rose 1.5%)
# hpi_delta_pct: % change in house price index
# rent_delta: percentage points change in annual rent growth rate
_RULES = [
    ("rate_shock_up",   lambda rd, hd, rend: rd > 1.5,           "Mortgages get costlier; prices may fall",      "rate_delta"),
    ("rate_shock_down", lambda rd, hd, rend: rd < -1.5,          "Cheaper borrowing; demand lifts prices",       "rate_delta"),
    ("rate_rise",       lambda rd, hd, rend: 0.5 < rd <= 1.5,    "Borrowing costs increasing",                   "rate_delta"),
    ("rate_cut",        lambda rd, hd, rend: -1.5 <= rd < -0.5,  "Borrowing costs easing",                       "rate_delta"),
    ("price_crash",     lambda rd, hd, rend: hd < -5.0,          "Market correction; portfolio loses value",     "hpi_delta_pct"),
    ("price_surge",     lambda rd, hd, rend: hd > 8.0,           "Boom conditions; hold and ride it",            "hpi_delta_pct"),
    ("rent_surge",      lambda rd, hd, rend: rend > 2.0,         "Income growing; landlords benefit",            "rent_delta"),
    ("rent_squeeze",    lambda rd, hd, rend: rend < -1.0,        "Rental income under pressure",                 "rent_delta"),
]


def detect_events(prev_entry, curr_entry, tick: int) -> list:
    """
    Compare two consecutive UK_MACRO entries and return event dicts for significant changes.

    prev_entry: (year, half, price_index, rate, rent_growth) or None (tick 0 — no events fired)
    curr_entry: (year, half, price_index, rate, rent_growth)
    tick: current simulation tick number (written into each event dict)
    """
    if prev_entry is None:
        return []

    _, _, prev_hpi, prev_rate, prev_rent, *_ = prev_entry
    _, _, curr_hpi, curr_rate, curr_rent, *_ = curr_entry

    rate_delta = curr_rate - prev_rate
    hpi_delta_pct = (curr_hpi - prev_hpi) / prev_hpi * 100
    rent_delta = curr_rent - prev_rent

    deltas = {"rate_delta": rate_delta, "hpi_delta_pct": hpi_delta_pct, "rent_delta": rent_delta}

    events = []
    for event_type, condition, detail, delta_key in _RULES:
        if condition(rate_delta, hpi_delta_pct, rent_delta):
            events.append({
                "type": event_type,
                "tick": tick,
                "detail": detail,
                "delta": round(deltas[delta_key], 2),
            })
    return events
