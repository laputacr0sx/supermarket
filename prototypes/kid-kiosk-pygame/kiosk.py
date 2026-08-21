"""Pygame 士多 till — same ViewModel as the HTML demo.

    python kiosk.py              # window, keys like the HTML remote
    python kiosk.py --fullscreen
    python kiosk.py --shots      # write PNG frames and quit (no click-through)

Keys: 1–6 scan · A 樂樂 · S 森 · C 清 · 7 上架蘋果 · F 全螢幕 · Esc 關
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pygame
import pygame.freetype

from shop import Shop, ViewModel
from store.kiosk.copy import COPY
from store.kiosk.fonts import find_cjk_font
from store.kiosk.typeface import Typeface

W, H = 1366, 768
HEADER_H = 88
FOOTER_H = 230
HINT_H = 52

WOOD = (42, 33, 24)
CREAM = (246, 239, 228)
PAPER = (255, 250, 242)
INK = (42, 33, 24)
HKRED = (200, 22, 29)
LEAF = (31, 122, 69)
MUTE = (138, 123, 107)
DIM = (201, 184, 164)
NOPE_BG = (248, 215, 208)
OK_BG = (220, 239, 224)
SOFT_BG = (255, 233, 179)
ROOM = (22, 18, 14)

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "kid-kiosk" / "assets"

BAR_WIDTHS = [4, 8, 4, 12, 6, 4, 10, 6, 4, 14, 4, 8, 4, 10, 6, 4, 12, 4, 8, 6]


def round_rect(surf: pygame.Surface, rect: pygame.Rect, color, radius: int) -> None:
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def blit_center(dst: pygame.Surface, src: pygame.Surface, cx: int, cy: int) -> pygame.Rect:
    r = src.get_rect(center=(cx, cy))
    dst.blit(src, r)
    return r


def load_photos() -> dict[str, pygame.Surface]:
    photos: dict[str, pygame.Surface] = {}
    for key in ("cereal", "milk", "tomato", "card"):
        path = ASSETS / f"{key}.jpg"
        if path.is_file():
            img = pygame.image.load(str(path)).convert()
            photos[key] = img
    return photos


def fit_in_box(img: pygame.Surface, box: int) -> pygame.Surface:
    w, h = img.get_size()
    scale = min(box / w, box / h)
    return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))


def rounded_photo(img: pygame.Surface, box: int, radius: int) -> pygame.Surface:
    fitted = fit_in_box(img, box)
    canvas = pygame.Surface((box, box), pygame.SRCALPHA)
    canvas.blit(fitted, fitted.get_rect(center=(box // 2, box // 2)))
    mask = pygame.Surface((box, box), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    canvas.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return canvas


def draw_barcode(dst: pygame.Surface, cx: int, cy: int) -> None:
    gap = 7
    total_w = len(BAR_WIDTHS) * gap
    x = cx - total_w // 2
    for h in BAR_WIDTHS:
        bar_h = h * 7
        pygame.draw.rect(dst, INK, (x, cy - bar_h // 2, 5, bar_h))
        x += gap


def draw_yuan(
    fonts: Typeface, n: int, num_size: int, color: tuple[int, int, int]
) -> pygame.Surface:
    num = fonts.render(str(n), num_size, color)
    unit = fonts.render(COPY.yuan, max(18, int(num_size * 0.42)), color)
    pad = max(4, num_size // 20)
    w = num.get_width() + pad + unit.get_width()
    h = max(num.get_height(), unit.get_height())
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.blit(num, (0, h - num.get_height()))
    surf.blit(unit, (num.get_width() + pad, h - unit.get_height() - num_size // 12))
    return surf


class Kiosk:
    def __init__(self, fullscreen: bool = False) -> None:
        pygame.init()
        pygame.freetype.init()
        flags = pygame.SCALED
        if fullscreen:
            flags |= pygame.FULLSCREEN
        self.fullscreen = fullscreen
        self.screen = pygame.display.set_mode((W, H + HINT_H), flags)
        pygame.display.set_caption(COPY.store)
        pygame.mouse.set_visible(False)
        pygame.event.set_blocked(
            (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)
        )
        self.clock = pygame.time.Clock()
        self.fonts = Typeface()
        self.photos = load_photos()
        self.shop = Shop()
        self.running = True

    def now_ms(self) -> int:
        return pygame.time.get_ticks()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode((W, H + (0 if self.fullscreen else HINT_H)), flags)

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        now = self.now_ms()
        scans = {
            pygame.K_1: "cereal",
            pygame.K_2: "milk",
            pygame.K_3: "tomato",
            pygame.K_4: "toothpaste",
            pygame.K_5: "apple",
            pygame.K_6: "junk",
        }
        if key in scans:
            self.shop.scan(scans[key], now)
        elif key == pygame.K_a:
            self.shop.tap("alex", now)
        elif key == pygame.K_s:
            self.shop.tap("sam", now)
        elif key == pygame.K_c:
            self.shop.clear()
        elif key == pygame.K_7:
            self.shop.finish_draft("2718403957618", "蘋果", 3)
        elif key == pygame.K_f:
            self.toggle_fullscreen()
        elif key == pygame.K_ESCAPE:
            if self.fullscreen:
                self.toggle_fullscreen()
            else:
                self.running = False

    def draw_stage(self, dest: pygame.Surface, vm: ViewModel) -> None:
        bg = CREAM
        if vm.flash == "ok":
            bg = OK_BG
        elif vm.flash == "nope":
            bg = NOPE_BG
        elif vm.flash == "soft":
            bg = SOFT_BG
        dest.fill(bg)

        pygame.draw.rect(dest, WOOD, (0, 0, W, HEADER_H))
        mark = self.fonts.render(vm.header, 48, CREAM)
        dest.blit(mark, (40, (HEADER_H - mark.get_height()) // 2))
        pill = self.fonts.render(vm.pill, 22, CREAM)
        pr = pygame.Rect(0, 0, pill.get_width() + 36, pill.get_height() + 16)
        pr.midright = (W - 40, HEADER_H // 2)
        pygame.draw.rect(dest, (58, 48, 40), pr, border_radius=999)
        dest.blit(pill, pill.get_rect(center=pr.center))

        hero_top = HEADER_H
        hero_bot = H - FOOTER_H
        cx = W // 2
        pic_box = 200
        pic_rect = pygame.Rect(0, 0, pic_box, pic_box)
        pic_rect.midtop = (cx, hero_top + 18)
        round_rect(dest, pic_rect, PAPER, 28)

        if vm.picture == "barcode":
            draw_barcode(dest, pic_rect.centerx, pic_rect.centery)
        elif vm.picture == "idle":
            cart = self.fonts.render(COPY.idle_glyph, 72, MUTE)
            blit_center(dest, cart, pic_rect.centerx, pic_rect.centery)
        else:
            key = "card" if vm.picture == "card" else vm.picture
            img = self.photos.get(key)
            if img:
                fitted = rounded_photo(img, pic_box, 28)
                dest.blit(fitted, pic_rect)
            else:
                q = self.fonts.render("？", 72, MUTE)
                blit_center(dest, q, pic_rect.centerx, pic_rect.centery)

        y = pic_rect.bottom + 8
        if vm.tag_yuan is not None:
            tag = draw_yuan(self.fonts, vm.tag_yuan, 96, HKRED)
            dest.blit(tag, tag.get_rect(midtop=(cx, y)))
            y += tag.get_height() + 2
        if vm.title:
            title = self.fonts.render(vm.title, 36, INK)
            dest.blit(title, title.get_rect(midtop=(cx, y)))
            y += title.get_height() + 2
        if vm.sub:
            sub = self.fonts.render(vm.sub, 26, MUTE)
            dest.blit(sub, sub.get_rect(midtop=(cx, y)))

        if vm.count:
            count = self.fonts.render(vm.count, 32, MUTE)
            dest.blit(count, (48, H - 78))

        if vm.sum_yuan is not None:
            style = {
                "hot": HKRED,
                "gold": LEAF,
                "need": (180, 35, 24),
                "dim": DIM,
                "": INK,
            }[vm.sum_style]
            yuan = draw_yuan(self.fonts, vm.sum_yuan, 120, style)
            xr = W - 48
            dest.blit(yuan, yuan.get_rect(bottomright=(xr, H - 22)))
            if vm.sum_label:
                lab = self.fonts.render(vm.sum_label, 36, MUTE)
                dest.blit(
                    lab,
                    lab.get_rect(bottomright=(xr - yuan.get_width() - 14, H - 36)),
                )

    def draw_hint(self, dest: pygame.Surface) -> None:
        bar = pygame.Rect(0, H, W, HINT_H)
        pygame.draw.rect(dest, ROOM, bar)
        text = self.fonts.render(
            "1 麥片   2 牛奶   3 蕃茄   4 牙膏   5 貼紙   6 亂碼    A 樂樂   S 森   C 清   7 上架蘋果   F 全螢幕",
            18,
            (203, 187, 166),
        )
        dest.blit(text, text.get_rect(center=bar.center))

    def paint(self) -> None:
        self.shop.tick(self.now_ms())
        vm = self.shop.view()
        stage = pygame.Surface((W, H))
        self.draw_stage(stage, vm)
        self.screen.fill(ROOM)
        self.screen.blit(stage, (0, 0))
        if not self.fullscreen:
            self.draw_hint(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle(event)
            self.paint()
            self.clock.tick(60)
        pygame.quit()


def write_shots(out_dir: Path) -> None:
    pygame.init()
    pygame.freetype.init()
    flags = pygame.HIDDEN | pygame.SCALED
    try:
        screen = pygame.display.set_mode((W, H), flags)
    except pygame.error:
        screen = pygame.display.set_mode((W, H))
    fonts = Typeface()
    photos = load_photos()
    kiosk = Kiosk.__new__(Kiosk)
    kiosk.fonts = fonts
    kiosk.photos = photos
    kiosk.fullscreen = True
    out_dir.mkdir(parents=True, exist_ok=True)

    frames: list[tuple[str, Shop]] = []

    idle = Shop()
    frames.append(("01-idle", idle))

    cereal = Shop()
    cereal.scan("cereal", 0)
    frames.append(("02-cereal", cereal))

    cart = Shop()
    cart.scan("cereal", 0)
    cart.scan("milk", 0)
    frames.append(("03-cart", cart))

    need = Shop()
    need.scan("cereal", 0)
    need.scan("milk", 0)
    need.tap("sam", 0)
    frames.append(("04-need", need))

    paid = Shop()
    paid.scan("cereal", 0)
    paid.scan("milk", 0)
    paid.tap("alex", 0)
    frames.append(("05-paid", paid))

    learned = Shop()
    learned.scan("toothpaste", 0)
    frames.append(("06-saved", learned))

    pending = Shop()
    pending.scan("apple", 0)
    frames.append(("07-pending", pending))

    unknown = Shop()
    unknown.scan("junk", 0)
    frames.append(("08-unknown", unknown))

    named = Shop()
    named.finish_draft("2718403957618", "蘋果", 3)
    named.scan("apple", 0)
    frames.append(("09-named", named))

    for name, shop in frames:
        kiosk.shop = shop
        stage = pygame.Surface((W, H))
        kiosk.draw_stage(stage, shop.view())
        path = out_dir / f"{name}.png"
        pygame.image.save(stage, str(path))
        print(path)
        screen.blit(stage, (0, 0))
        pygame.display.flip()

    pygame.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{COPY.store} pygame till")
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--shots", action="store_true", help="render PNG frames and exit")
    args = parser.parse_args()
    if args.shots:
        write_shots(HERE / "shots")
        return 0
    if find_cjk_font() is None:
        print("No CJK font found; Chinese glyphs may be boxes.", file=sys.stderr)
    Kiosk(fullscreen=args.fullscreen).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
