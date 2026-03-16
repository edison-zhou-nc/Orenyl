import pytest

from lore.handlers._common import (
    _clamp_non_negative_int,
    _clamp_positive_int,
    _decode_cursor,
    _encode_cursor,
)


def test_clamp_positive_int_enforces_lower_and_upper_bounds():
    assert _clamp_positive_int(0, 100, 200) == 1
    assert _clamp_positive_int(999, 100, 200) == 200


def test_clamp_non_negative_int_enforces_floor_without_upper_bound():
    assert _clamp_non_negative_int(-5, 7) == 0
    assert _clamp_non_negative_int("bad", 7) == 7
    assert _clamp_non_negative_int(999999, 7) == 999999


def test_cursor_helpers_round_trip_created_at_and_item_id():
    cursor = _encode_cursor("2026-03-15T00:00:00Z", "event:1")
    assert _decode_cursor(cursor) == ("2026-03-15T00:00:00Z", "event:1")


def test_decode_cursor_rejects_invalid_input():
    with pytest.raises(ValueError, match="invalid_cursor"):
        _decode_cursor("not-a-cursor")
