from store.io.scanner import assemble


def _downs(digits: str) -> list[tuple[str, int]]:
    events: list[tuple[str, int]] = []
    for ch in digits:
        name = "KEY_0" if ch == "0" else f"KEY_{ch}"
        events.append((name, 1))
        events.append((name, 0))
    events.append(("KEY_ENTER", 1))
    events.append(("KEY_ENTER", 0))
    return events


def test_enter_emits_one_barcode():
    assert assemble(_downs("5901234123457")) == ["5901234123457"]


def test_two_scans_in_one_stream():
    stream = _downs("5901234123457") + _downs("4890000000017")
    assert assemble(stream) == ["5901234123457", "4890000000017"]


def test_ignores_auto_repeat():
    events = [("KEY_5", 1), ("KEY_5", 2), ("KEY_9", 1), ("KEY_ENTER", 1)]
    assert assemble(events) == ["59"]


def test_incomplete_without_enter_is_empty():
    assert assemble([("KEY_5", 1), ("KEY_9", 1)]) == []


def test_key_up_does_not_duplicate():
    events = [("KEY_1", 1), ("KEY_1", 0), ("KEY_2", 1), ("KEY_2", 0), ("KEY_ENTER", 1)]
    assert assemble(events) == ["12"]


def test_keypad_enter():
    events = [("KEY_KP5", 1), ("KEY_KP9", 1), ("KEY_KPENTER", 1)]
    assert assemble(events) == ["59"]
