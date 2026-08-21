"""Pygame key helpers. Constants match pygame.KMOD_* / pygame.K_p."""

from __future__ import annotations

# pygame.KMOD_SHIFT / CTRL / ALT are left|right ORs. A left-only chord
# sets one side, so `mod & KMOD_CTRL == KMOD_CTRL` is never true.
KMOD_SHIFT = 0x0003
KMOD_CTRL = 0x00C0
KMOD_ALT = 0x0300
K_P = 112  # pygame.K_p


def is_staff_chord(key: int, mod: int) -> bool:
    if key not in {K_P, 80}:  # pygame.K_p, or 'P' on some layouts
        return False
    return bool(mod & KMOD_CTRL) and bool(mod & KMOD_ALT) and bool(mod & KMOD_SHIFT)
