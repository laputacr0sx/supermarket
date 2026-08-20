from store.io.nfc import accept_tap, normalize_uid


def test_normalize_strips_colons_and_spaces():
    assert normalize_uid("de:ad be:ef") == "DEADBEEF"


def test_normalize_rejects_non_hex():
    import pytest

    with pytest.raises(ValueError):
        normalize_uid("hello")


def test_debounce_same_uid_within_window():
    first = accept_tap(None, 0.0, "DEADBEEF", now=1.0, window_s=2.0)
    assert first is not None
    again = accept_tap(first, 1.0, "DEADBEEF", now=2.5, window_s=2.0)
    assert again is None


def test_debounce_allows_after_window():
    first = accept_tap(None, 0.0, "DEADBEEF", now=1.0, window_s=2.0)
    later = accept_tap(first, 1.0, "DEADBEEF", now=3.1, window_s=2.0)
    assert later == "DEADBEEF"


def test_other_uid_is_not_debounced():
    first = accept_tap(None, 0.0, "DEADBEEF", now=1.0, window_s=2.0)
    other = accept_tap(first, 1.0, "CAFEBABE", now=1.1, window_s=2.0)
    assert other == "CAFEBABE"
