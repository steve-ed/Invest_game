# UK Regional HPI Multipliers
#
# get_regional_multiplier(year, region) returns a multiplier applied to the
# national growth rate for that region in that year.
# Derived from approximate UK regional HPI divergence patterns.

_BASE = {
    'London':   1.40,
    'South':    1.20,
    'East':     1.10,
    'West':     1.00,
    'Midlands': 0.90,
    'North':    0.80,
    'Scotland': 0.85,
    'Wales':    0.75,
}

# (start_year, end_year_inclusive, {region: multiplier})
_ERA_OVERRIDES = [
    # London/South boom and bust 1987-1993
    (1987, 1989, {'London': 1.80, 'South': 1.50, 'North': 0.65, 'Wales': 0.60}),
    (1990, 1995, {'London': 1.60, 'South': 1.40, 'North': 0.70, 'Wales': 0.65}),
    # Mid-nineties — London surges ahead
    (1996, 2000, {'London': 1.80, 'South': 1.50, 'North': 0.75}),
    # Pre-GFC London/South outperformance
    (2001, 2007, {'London': 1.60, 'South': 1.40, 'East': 1.20}),
    # GFC: convergence — London falls harder
    (2008, 2012, {'London': 0.90, 'South': 0.95, 'North': 1.05, 'Midlands': 1.00}),
    # Post-GFC London surge (Help to Buy era)
    (2013, 2016, {'London': 2.00, 'South': 1.60, 'East': 1.30}),
    # Post-Brexit: London cools, Midlands/North catch up
    (2017, 2020, {'London': 0.70, 'South': 0.80, 'North': 1.10, 'Midlands': 1.15, 'Wales': 1.10}),
    # Rate shock 2022-2024: London most exposed (high debt/value)
    (2021, 2024, {'London': 0.75, 'South': 0.85, 'North': 1.05, 'Midlands': 1.10}),
]


def get_regional_multiplier(year, region):
    """Return growth multiplier for region in year relative to national."""
    for start, end, overrides in _ERA_OVERRIDES:
        if start <= year <= end and region in overrides:
            return overrides[region]
    return _BASE.get(region, 1.0)
