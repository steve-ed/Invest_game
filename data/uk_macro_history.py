# UK Macro History — semi-annual data 1983 H1 → 2024 H2
#
# IMPORTANT: Values are APPROXIMATE / ILLUSTRATIVE.
# Derived from my training knowledge of major trends in:
#   - Nationwide / Halifax House Price Index
#   - Bank of England base rate
#   - ONS / VOA private rental growth estimates
#   - ONS CPI / RPI (RPI pre-2004, CPI from 2004)
#
# Authoritative sources for verification / replacement:
#   BoE rates:    bankofengland.co.uk/statistics (series IUDSOIA / IUMABEDR)
#   House prices: nationwidehousepriceindex.co.uk (download tab)
#   Rental:       ons.gov.uk/economy/inflationandpriceindices/datasets/
#                 indexofprivatehousingrentalprices (from 2011 only)
#   CPI/RPI:      ons.gov.uk/economy/inflationandpriceindices
#
# price_index : 100 = 1983 H1 baseline (~£31k UK avg)
# rate        : BoE base rate % at mid-period
# rent_growth : estimated annualised private rental growth %
# cpi         : annualised UK CPI/RPI % (RPI pre-2004, CPI from 2004)

UK_MACRO = [
    # year  half  price_index   rate   rent_growth  cpi
    (1983,  1,    100.0,        10.5,  3.0,         5.0),
    (1983,  2,    103.0,         9.1,  3.0,         4.5),
    (1984,  1,    106.0,         9.0,  3.5,         5.0),
    (1984,  2,    110.0,        10.5,  3.5,         5.0),
    (1985,  1,    116.0,        12.0,  4.0,         6.5),
    (1985,  2,    119.0,        11.5,  4.0,         5.5),
    (1986,  1,    129.0,        11.0,  4.5,         3.5),
    (1986,  2,    139.0,        10.5,  4.5,         3.0),
    (1987,  1,    152.0,         9.5,  5.0,         4.0),
    (1987,  2,    171.0,         9.0,  5.0,         4.5),
    (1988,  1,    187.0,         8.5,  5.5,         4.5),  # Housing Act 1988 — deregulation
    (1988,  2,    203.0,        12.0,  5.5,         6.5),
    (1989,  1,    213.0,        13.5,  6.0,         7.5),  # Peak of boom
    (1989,  2,    213.0,        15.0,  6.0,         7.5),  # Rates hit 15%
    (1990,  1,    210.0,        15.0,  5.5,         9.5),
    (1990,  2,    200.0,        14.0,  5.0,         9.0),  # Bust beginning
    (1991,  1,    190.0,        12.0,  4.5,         6.0),
    (1991,  2,    184.0,        10.5,  4.0,         4.5),
    (1992,  1,    177.0,        10.0,  3.5,         4.0),
    (1992,  2,    171.0,         7.0,  3.0,         3.0),  # Black Wednesday — ERM exit Sep 92
    (1993,  1,    168.0,         6.0,  2.5,         2.5),  # Trough
    (1993,  2,    171.0,         5.5,  2.5,         2.0),
    (1994,  1,    174.0,         5.5,  3.0,         2.5),
    (1994,  2,    177.0,         6.0,  3.0,         2.5),
    (1995,  1,    177.0,         6.5,  3.5,         3.0),
    (1995,  2,    181.0,         6.5,  3.5,         3.5),
    (1996,  1,    187.0,         6.0,  4.0,         2.5),
    (1996,  2,    194.0,         6.0,  4.0,         2.5),
    (1997,  1,    203.0,         6.0,  4.5,         3.0),  # Labour win; BoE independence
    (1997,  2,    219.0,         7.0,  4.5,         3.5),
    (1998,  1,    232.0,         7.5,  4.5,         3.0),
    (1998,  2,    242.0,         6.5,  4.5,         3.0),
    (1999,  1,    255.0,         5.5,  4.0,         2.5),
    (1999,  2,    274.0,         5.5,  4.0,         2.0),
    (2000,  1,    294.0,         6.0,  4.5,         3.0),
    (2000,  2,    319.0,         6.0,  4.5,         3.0),
    (2001,  1,    345.0,         5.5,  4.0,         2.5),  # Dotcom bust — BoE cuts
    (2001,  2,    371.0,         4.0,  4.0,         1.5),  # 9/11 — further cuts
    (2002,  1,    416.0,         4.0,  3.5,         1.5),
    (2002,  2,    481.0,         4.0,  3.5,         2.5),
    (2003,  1,    510.0,         3.75, 3.5,         3.0),
    (2003,  2,    526.0,         3.75, 3.5,         2.5),
    (2004,  1,    526.0,         4.25, 3.5,         2.0),  # Price plateau
    (2004,  2,    526.0,         4.75, 3.5,         2.0),
    (2005,  1,    523.0,         4.75, 3.0,         2.0),
    (2005,  2,    532.0,         4.5,  3.0,         2.5),
    (2006,  1,    548.0,         4.5,  3.5,         2.5),
    (2006,  2,    581.0,         5.0,  3.5,         3.0),
    (2007,  1,    603.0,         5.5,  4.0,         2.5),  # Pre-GFC peak
    (2007,  2,    629.0,         5.75, 4.0,         2.5),  # Northern Rock Sep 2007
    (2008,  1,    613.0,         5.0,  3.5,         3.5),
    (2008,  2,    548.0,         2.0,  3.0,         5.0),  # Lehman Sep 08 — rapid cuts
    (2009,  1,    500.0,         0.5,  1.5,         2.0),  # Rates floored
    (2009,  2,    532.0,         0.5,  1.5,         1.5),
    (2010,  1,    548.0,         0.5,  2.5,         3.5),
    (2010,  2,    539.0,         0.5,  2.5,         4.0),
    (2011,  1,    532.0,         0.5,  3.5,         4.5),
    (2011,  2,    526.0,         0.5,  3.5,         5.0),
    (2012,  1,    526.0,         0.5,  3.5,         3.5),
    (2012,  2,    532.0,         0.5,  3.5,         2.5),
    (2013,  1,    542.0,         0.5,  2.5,         3.0),
    (2013,  2,    571.0,         0.5,  2.5,         2.5),
    (2014,  1,    597.0,         0.5,  2.5,         2.0),
    (2014,  2,    613.0,         0.5,  2.5,         1.5),
    (2015,  1,    623.0,         0.5,  3.0,         0.5),
    (2015,  2,    635.0,         0.5,  3.0,         0.0),
    (2016,  1,    652.0,         0.5,  2.5,         0.5),  # Brexit vote Jun 2016
    (2016,  2,    671.0,         0.25, 2.5,         1.5),  # BoE cuts post-Brexit
    (2017,  1,    694.0,         0.25, 2.0,         2.5),
    (2017,  2,    697.0,         0.5,  2.0,         3.0),
    (2018,  1,    697.0,         0.5,  2.0,         2.5),
    (2018,  2,    687.0,         0.75, 2.0,         2.5),
    (2019,  1,    694.0,         0.75, 2.5,         2.0),
    (2019,  2,    703.0,         0.75, 2.5,         1.5),
    (2020,  1,    694.0,         0.1,  1.0,         1.0),  # COVID lockdowns — BoE emergency cut
    (2020,  2,    790.0,         0.1,  1.0,         0.5),  # Stamp duty holiday — price surge
    (2021,  1,    832.0,         0.1,  2.5,         2.0),
    (2021,  2,    877.0,         0.25, 4.0,         5.0),
    (2022,  1,    903.0,         1.0,  7.5,         8.0),  # Rapid rate hikes — inflation surge
    (2022,  2,    952.0,         3.5,  9.5,        11.0),  # Peak prices
    (2023,  1,    861.0,         4.5,  9.5,         9.0),  # Correction
    (2023,  2,    832.0,         5.25, 8.5,         6.0),
    (2024,  1,    842.0,         5.25, 7.0,         3.5),  # Slow recovery
    (2024,  2,    865.0,         4.75, 6.5,         2.5),
]

# Named eras — revealed at game end
# Each entry: (start_year, end_year_inclusive, label)
ERA_LABELS = [
    (1983, 1985, "Early Thatcher Recovery"),
    (1986, 1989, "Late Thatcher Boom"),
    (1989, 1995, "Boom & Bust — The 1989 Crash"),
    (1993, 1999, "Mid-Nineties Recovery & Cool Britannia"),
    (1997, 2004, "New Labour Boom — Part I"),
    (2001, 2008, "Long Boom & The Run-Up to the GFC"),
    (2007, 2014, "The Global Financial Crisis & Austerity"),
    (2010, 2017, "Post-GFC Long Recovery"),
    (2013, 2020, "Sustained Growth, Brexit & COVID"),
    (2018, 2024, "Rate Shock Cycle — COVID Boom to Normalisation"),
]

def _build_quarterly():
    """Interpolate UK_MACRO semi-annual data into quarterly entries."""
    result = []
    for i, entry in enumerate(UK_MACRO):
        year, half, pi, rate, rent, cpi = entry
        quarter = 1 if half == 1 else 3
        result.append((year, quarter, pi, rate, rent, cpi))
        if i + 1 < len(UK_MACRO):
            ny, nh, npi, nrate, nrent, ncpi = UK_MACRO[i + 1]
            result.append((
                year,
                quarter + 1,
                round((pi + npi) / 2, 1),
                round((rate + nrate) / 2, 2),
                round((rent + nrent) / 2, 1),
                round((cpi + ncpi) / 2, 1),
            ))
    return result


UK_MACRO_QUARTERLY = _build_quarterly()


def get_quarterly_start_limits(total_quarterly_ticks):
    """Return (min_year, max_year) for quarterly game of given length."""
    max_start_idx = len(UK_MACRO_QUARTERLY) - total_quarterly_ticks - 1
    if max_start_idx < 0:
        raise ValueError(
            f"Not enough quarterly data for {total_quarterly_ticks} ticks "
            f"(have {len(UK_MACRO_QUARTERLY)})"
        )
    return UK_MACRO_QUARTERLY[0][0], UK_MACRO_QUARTERLY[max_start_idx][0]


def get_quarterly_slice(start_year, start_quarter, count):
    """Return `count` consecutive quarterly entries from (start_year, start_quarter)."""
    idx = next(
        (i for i, e in enumerate(UK_MACRO_QUARTERLY)
         if e[0] == start_year and e[1] == start_quarter),
        None
    )
    if idx is None:
        raise ValueError(f"No quarterly data for {start_year} Q{start_quarter}")
    if idx + count > len(UK_MACRO_QUARTERLY):
        raise ValueError(
            f"Not enough quarterly data: need {count} from index {idx}, "
            f"have {len(UK_MACRO_QUARTERLY)}"
        )
    return UK_MACRO_QUARTERLY[idx:idx + count]


def get_era_label(start_year):
    """Return the era label for a given start year (best match)."""
    best = ERA_LABELS[0][2]
    for s, e, label in ERA_LABELS:
        if s <= start_year <= e:
            best = label
    return best


def get_start_limits(total_ticks):
    """
    Return (min_year, max_year) for random start selection.
    Ensures enough data remains to cover the game length.
    total_ticks: number of semi-annual periods needed.
    """
    max_start_idx = len(UK_MACRO) - total_ticks - 1  # -1 guards against start_half=2 adding one index
    if max_start_idx < 0:
        raise ValueError(f"Not enough data for {total_ticks} ticks (have {len(UK_MACRO)})")
    min_year = UK_MACRO[0][0]
    max_year = UK_MACRO[max_start_idx][0]
    return min_year, max_year


def get_slice(start_year, start_half, count):
    """
    Return `count` consecutive entries starting from (start_year, start_half).
    Raises ValueError if not enough data.
    """
    idx = None
    for i, entry in enumerate(UK_MACRO):
        if entry[0] == start_year and entry[1] == start_half:
            idx = i
            break
    if idx is None:
        raise ValueError(f"No data for {start_year} H{start_half}")
    if idx + count > len(UK_MACRO):
        raise ValueError(f"Not enough data: need {count} entries from index {idx}, have {len(UK_MACRO)}")
    return UK_MACRO[idx:idx + count]
