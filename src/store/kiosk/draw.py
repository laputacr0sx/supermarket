"""Paint a ViewModel. pygame is imported by the caller."""

from __future__ import annotations

from pathlib import Path

from store.kiosk.fsm import ViewModel

W, H = 1366, 768
HEADER_H = 88
FOOTER_H = 230
WOOD = (42, 33, 24)
CREAM = (246, 239, 228)
PAPER = (255, 250, 242)
INK = (42, 33, 24)
HKRED = (200, 22, 29)
MUTE = (138, 123, 107)
NOPE_BG = (248, 215, 208)
OK_BG = (220, 239, 224)
SOFT_BG = (255, 233, 179)

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    Path(r"C:\Windows\Fonts\msjhbd.ttc"),
    Path(r"C:\Windows\Fonts\msjh.ttc"),
]


def find_cjk_font() -> str | None:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return str(path)
    return None


def paint(pygame, fonts, dest, vm: ViewModel) -> None:
    bg = CREAM
    if vm.flash == "ok":
        bg = OK_BG
    elif vm.flash == "nope":
        bg = NOPE_BG
    elif vm.flash == "soft":
        bg = SOFT_BG
    dest.fill(bg)
    pygame.draw.rect(dest, WOOD, (0, 0, W, HEADER_H))
    mark = fonts.render(vm.header, 48, CREAM)
    dest.blit(mark, (40, (HEADER_H - mark.get_height()) // 2))
    cx = W // 2
    y = HEADER_H + 40
    if vm.tag_yuan is not None:
        tag = fonts.render(f"{vm.tag_yuan}元", 96, HKRED)
        dest.blit(tag, tag.get_rect(midtop=(cx, y)))
        y += tag.get_height() + 8
    if vm.title:
        title = fonts.render(vm.title, 48, INK)
        dest.blit(title, title.get_rect(midtop=(cx, y)))
        y += title.get_height() + 8
    if vm.sub:
        sub = fonts.render(vm.sub, 28, MUTE)
        dest.blit(sub, sub.get_rect(midtop=(cx, y)))
    footer = pygame.Rect(0, H - FOOTER_H, W, FOOTER_H)
    pygame.draw.rect(dest, PAPER, footer)
    if vm.sum_yuan is not None:
        label = fonts.render(f"{vm.sum_label} {vm.sum_yuan}元", 64, HKRED)
        dest.blit(label, label.get_rect(center=footer.center))
    if vm.count:
        count = fonts.render(vm.count, 28, MUTE)
        dest.blit(count, (40, H - FOOTER_H + 24))
