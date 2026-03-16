import pytest

from lore.handlers._common import (
    _clamp_non_negative_int,
    _clamp_positive_int,
    _decode_cursor,
    _encode_cursor,
)


def test_handler_common_numeric_and_cursor_helpers():
    assert _clamp_positive_int(0, 100, 200) == 1
    assert _clamp_positive_int(999, 100, 200) == 200
    assert _clamp_non_negative_int(-5, 7) == 0
    assert _clamp_non_negative_int("bad", 7) == 7
    cursor = _encode_cursor("2026-03-15T00:00:00Z", "event:1")
    assert _decode_cursor(cursor) == ("2026-03-15T00:00:00Z", "event:1")

    with pytest.raises(ValueError, match="invalid_cursor"):
        _decode_cursor("not-a-cursor")
