def label_from_deltas(rate_delta: float, hpi_delta_pct: float) -> str:
    """
    Derive a human-readable scenario label from consecutive UK_MACRO entry deltas.

    rate_delta: change in interest rate in percentage points (e.g. +1.5 = rates rose 1.5%)
    hpi_delta_pct: percentage change in house price index (e.g. -5.0 = prices fell 5%)
    """
    if hpi_delta_pct < -3.0 or rate_delta > 1.5:
        return "downturn"
    if hpi_delta_pct > 5.0:
        return "boom"
    return "baseline"
