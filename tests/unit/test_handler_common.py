from lore.handlers._common import _clamp_positive_int, _decode_cursor, _encode_cursor


def test_handler_common_numeric_and_cursor_helpers():
    assert _clamp_positive_int(0, 100, 200) == 1
    cursor = _encode_cursor("2026-03-15T00:00:00Z", "event:1")
    assert _decode_cursor(cursor) == ("2026-03-15T00:00:00Z", "event:1")
