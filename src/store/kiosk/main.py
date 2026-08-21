"""Kid till window. Needs pygame-ce (`uv sync --extra kiosk`)."""

from __future__ import annotations

import argparse
import time
from typing import Any

from store.config import get_settings
from store.io.scanner import assemble
from store.kiosk.client import Api
from store.kiosk.draw import H, W, find_cjk_font, paint
from store.kiosk.fsm import (
    Barcode,
    Effect,
    Key,
    KioskState,
    StaffUnlock,
    Tick,
    Uid,
    idle,
    step,
    view,
)

DEMO = {
    "a": "DEADBEEF",
    "s": "CAFEBABE",
}


def _apply(state: KioskState, effect: Effect, api: Api) -> KioskState:
    if effect.kind == "scan" and effect.code:
        return step(state, api.scan(effect.code), now=time.monotonic())[0]
    if effect.kind == "checkout" and effect.uid:
        return step(state, api.pay(effect.uid, effect.items), now=time.monotonic())[0]
    if effect.kind == "card" and effect.uid:
        return step(state, api.card(effect.uid), now=time.monotonic())[0]
    if effect.kind == "ledger" and effect.uid and effect.ledger_kind:
        reply = api.ledger(effect.uid, effect.ledger_kind, effect.amount_cents)
        return step(state, reply, now=time.monotonic())[0]
    if effect.kind == "void":
        return step(state, api.void_last(), now=time.monotonic())[0]
    return state


def run() -> None:
    parser = argparse.ArgumentParser(prog="store-kiosk")
    parser.add_argument("--fullscreen", action="store_true")
    args = parser.parse_args()
    import pygame
    import pygame.freetype

    pygame.init()
    pygame.freetype.init()
    flags = pygame.SCALED | (pygame.FULLSCREEN if args.fullscreen else 0)
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("士多")
    pygame.mouse.set_visible(False)
    font_path = find_cjk_font()
    cache: dict[int, Any] = {}

    def fonts_render(text: str, size: int, color: tuple[int, int, int]) -> object:
        if size not in cache:
            font = pygame.freetype.Font(font_path, size)
            font.pad = True
            cache[size] = font
        surf, _ = cache[size].render(text, color)
        return surf

    class Fonts:
        render = staticmethod(fonts_render)

    settings = get_settings()
    api = Api(f"http://{settings.pos_host}:{settings.pos_port}")
    state = idle()
    keys: list[tuple[str, int]] = []
    pin: list[str] = []
    waiting_pin = False
    running = True
    clock = pygame.time.Clock()
    mods_staff = pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_SHIFT
    fkeys = {
        pygame.K_F5: "F5",
        pygame.K_F6: "F6",
        pygame.K_F7: "F7",
        pygame.K_F8: "F8",
        pygame.K_F10: "F10",
    }
    try:
        while running:
            now = time.monotonic()
            state, _ = step(state, Tick(), now=now)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if state.mode in {"staff", "staff_queued"}:
                            state, _ = step(state, Key("Escape"), now=now)
                        else:
                            running = False
                    elif waiting_pin:
                        if event.unicode.isdigit():
                            pin.append(event.unicode)
                            if len(pin) >= 4:
                                waiting_pin = False
                                if "".join(pin) == settings.staff_pin:
                                    state, _ = step(state, StaffUnlock(), now=now)
                                pin = []
                    elif (
                        event.key == pygame.K_p
                        and event.mod & mods_staff == mods_staff
                    ):
                        waiting_pin = True
                        pin = []
                    elif event.key in fkeys:
                        state, effect = step(state, Key(fkeys[event.key]), now=now)
                        state = _apply(state, effect, api)
                    elif event.key == pygame.K_RETURN:
                        codes = assemble(keys + [("KEY_ENTER", 1)])
                        keys = []
                        for code in codes:
                            state, effect = step(state, Barcode(code), now=now)
                            state = _apply(state, effect, api)
                    elif event.unicode.lower() in DEMO:
                        state, effect = step(state, Uid(DEMO[event.unicode.lower()]), now=now)
                        state = _apply(state, effect, api)
                    elif event.unicode.isdigit():
                        name = "KEY_0" if event.unicode == "0" else f"KEY_{event.unicode}"
                        keys.append((name, 1))
            paint(pygame, Fonts, screen, view(state))
            pygame.display.flip()
            clock.tick(30)
    finally:
        api.close()
        pygame.quit()


if __name__ == "__main__":
    run()
