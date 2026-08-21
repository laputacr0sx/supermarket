"""pygame.freetype renderer: Free HK Kai, with a CJK fallback for missing glyphs."""

from __future__ import annotations

from typing import Any

import pygame.freetype

from store.kiosk.fonts import find_cjk_font, find_fallback_font, is_kai


class Typeface:
    def __init__(self) -> None:
        pygame.freetype.init()
        self.primary = find_cjk_font()
        self.fallback = find_fallback_font()
        self._cache: dict[tuple[str, int], Any] = {}

    def _font(self, path: str | None, size: int) -> Any:
        key = (path or "", size)
        if key not in self._cache:
            font = pygame.freetype.Font(path, size)
            font.pad = True
            font.strong = not is_kai(path)
            self._cache[key] = font
        return self._cache[key]

    def _has_glyph(self, font: Any, ch: str) -> bool:
        metrics = font.get_metrics(ch)
        return bool(metrics) and metrics[0] is not None

    def render(self, text: str, size: int, color: tuple[int, int, int]) -> Any:
        primary = self._font(self.primary, size)
        if not text:
            surf, _ = primary.render(" ", color)
            return surf
        if all(self._has_glyph(primary, ch) for ch in text):
            surf, _ = primary.render(text, color)
            return surf
        # Whole string, not per glyph: mixing kai + 黑體 in one word looks broken.
        fallback = self._font(self.fallback, size)
        surf, _ = fallback.render(text, color)
        return surf
