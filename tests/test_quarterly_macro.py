import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data'))
import uk_macro_history as hist


def test_quarterly_has_roughly_double_entries():
    # 82 semi-annual → ~163 quarterly (last entry has no midpoint after it)
    assert len(hist.UK_MACRO_QUARTERLY) == len(hist.UK_MACRO) * 2 - 1


def test_quarterly_starts_at_same_year():
    assert hist.UK_MACRO_QUARTERLY[0][0] == hist.UK_MACRO[0][0]


def test_quarterly_first_entry_matches_semi_annual():
    q = hist.UK_MACRO_QUARTERLY[0]
    s = hist.UK_MACRO[0]
    assert q[2] == s[2]   # price_index
    assert q[3] == s[3]   # rate


def test_quarterly_interpolated_entry_is_midpoint():
    s0 = hist.UK_MACRO[0]
    s1 = hist.UK_MACRO[1]
    mid = hist.UK_MACRO_QUARTERLY[1]
    expected_pi = round((s0[2] + s1[2]) / 2, 1)
    assert abs(mid[2] - expected_pi) < 0.01


def test_get_quarterly_slice_returns_correct_count():
    slc = hist.get_quarterly_slice(1990, 1, 40)
    assert len(slc) == 40


def test_get_quarterly_slice_raises_on_missing_start():
    try:
        hist.get_quarterly_slice(1800, 1, 5)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_get_quarterly_start_limits_short_game():
    min_y, max_y = hist.get_quarterly_start_limits(40)
    assert min_y == hist.UK_MACRO_QUARTERLY[0][0]
    assert max_y >= min_y


def test_get_quarterly_start_limits_long_game():
    min_y, max_y = hist.get_quarterly_start_limits(80)
    assert max_y < 2024  # must leave 80 entries after start
