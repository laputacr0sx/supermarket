from store.kiosk.keys import K_P, KMOD_ALT, KMOD_CTRL, KMOD_SHIFT, is_staff_chord

_LEFT = 0x0040 | 0x0100 | 0x0001  # LCTRL | LALT | LSHIFT
_BOTH = KMOD_CTRL | KMOD_ALT | KMOD_SHIFT


def test_left_only_chord_unlocks() -> None:
    assert is_staff_chord(K_P, _LEFT)


def test_both_sides_chord_unlocks() -> None:
    assert is_staff_chord(K_P, _BOTH)


def test_missing_shift_is_ignored() -> None:
    assert not is_staff_chord(K_P, 0x0040 | 0x0100)


def test_p_without_mods_is_ignored() -> None:
    assert not is_staff_chord(K_P, 0)


def test_other_key_with_mods_is_ignored() -> None:
    assert not is_staff_chord(ord("a"), _LEFT)


def test_old_equality_check_rejects_left_only() -> None:
    """The bug: pygame.KMOD_CTRL is L|R, so left-only never equals the mask."""
    assert (_LEFT & _BOTH) != _BOTH
