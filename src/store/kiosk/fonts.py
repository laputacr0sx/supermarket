"""Resolve a Traditional Chinese face for pygame.freetype."""

from __future__ import annotations

from pathlib import Path

KAI_FILENAME = "Free-HK-Kai_4700-v1.02.ttf"


def font_candidates() -> list[Path]:
    bundled = Path(__file__).resolve().parent / "fonts" / KAI_FILENAME
    repo = Path(__file__).resolve().parents[3]
    home = Path.home()
    return [
        bundled,
        repo / "assets" / "fonts" / KAI_FILENAME,
        home / "Downloads" / KAI_FILENAME,
        Path(r"C:\Windows\Fonts\msjhbd.ttc"),
        Path(r"C:\Windows\Fonts\msjh.ttc"),
        Path(r"C:\Windows\Fonts\mingliu.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]


def is_kai(path: str | None) -> bool:
    if path is None:
        return False
    return "kai" in Path(path).name.lower()


def find_cjk_font() -> str | None:
    for path in font_candidates():
        if path.is_file():
            return str(path)
    return None


def find_fallback_font() -> str | None:
    """Second face for Cantonese chars the 4700-glyph kai file omits (嘢, 咗, …)."""
    for path in font_candidates():
        if path.is_file() and not is_kai(str(path)):
            return str(path)
    return None
