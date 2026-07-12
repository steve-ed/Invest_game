import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
from uk_regional_hpi import get_regional_multiplier


def test_london_outperforms_national_in_late_nineties_boom():
    m = get_regional_multiplier(1999, 'London')
    assert m > 1.2, f"Expected London > 1.2 in 1999 boom, got {m}"


def test_north_underperforms_in_boom():
    m = get_regional_multiplier(1999, 'North')
    assert m < 1.0, f"Expected North < 1.0 in 1999, got {m}"


def test_london_underperforms_post_brexit():
    m = get_regional_multiplier(2019, 'London')
    assert m < 1.0, f"Expected London < 1.0 post-Brexit (2019), got {m}"


def test_midlands_tracks_national_broadly():
    m = get_regional_multiplier(2005, 'Midlands')
    assert 0.7 <= m <= 1.3, f"Midlands should be near national, got {m}"


def test_unknown_region_returns_one():
    m = get_regional_multiplier(2000, 'Atlantis')
    assert m == 1.0


def test_all_known_regions_have_multipliers():
    regions = ['London', 'South', 'East', 'West', 'Midlands', 'North', 'Scotland', 'Wales']
    for r in regions:
        m = get_regional_multiplier(2000, r)
        assert 0.3 <= m <= 3.0, f"Multiplier for {r} out of range: {m}"
