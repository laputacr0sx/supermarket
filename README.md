# Play supermarket

A Linux kiosk checkout for a toy shop: USB barcode scanner, NFC debit cards, money in SQLite, kid-facing UI on a Fujitsu LIFEBOOK LH772 (16 GB, SSD).

Children scan and tap. Parents top up from a staff-unlocked keyboard or a phone on the LAN. Cards hold a UID only.

Products are EAN-13: real household packs keep their factory code; toys get a **random** in-store EAN-13 on an A4 sheet that kids cut and tape. An unknown valid scan becomes a draft; an adult finishes name, price, and photo on the phone.

**Implementation contract:** [docs/implementation-plan.md](docs/implementation-plan.md)

**Git:** [CONTRIBUTING.md](CONTRIBUTING.md) — `main` stays green; short-lived branches; squash-merge PRs. Home and work both clone this GitHub repo; do not copy folders.

**Another machine (first time):** install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then the same commands on macOS, Windows, and Linux:

```
git clone https://github.com/laputacr0sx/supermarket.git
cd supermarket
uv sync
uv run pytest
```

Python **3.12** (pinned in `.python-version`; uv installs it). Each PC has its own `.venv` and SQLite file (`data/` is not in git). On a new Windows box also set LF (once): `git config --global core.autocrlf false` and `git config --global core.eol lf`.

That plan locks hardware, OS/kiosk (Cage + Openbox fallback), **pygame-ce** for the kid till, process split (`store-api` / `store-kiosk`), schema, API, state machine, and build phases 0–8.

**Phase 2 (same commands on every OS; gun grab waits for the LIFEBOOK):**

```
uv sync
uv run pytest
uv run store-seed
uv run store-doctor
uv run store-api
```

Phone admin (same process): `http://<this-pc>:8788` — set `STORE_ADMIN_PASSWORD` or admin stays locked. Unfinished drafts (name / 元 / camera photo), typed pantry barcodes, 貨架, 開卡 / 充值, 今日銷售, 印一張標籤 / 再印.

In another terminal:

```
uv run store-scan 4890000000010
uv run store-labels data/labels.pdf
```

`store-scan` POSTs to `http://127.0.0.1:8787/pos/scan`. Ready cereal prints the name; a new valid pack prints `learned`; garbage prints `reject`. `store-labels` mints a Rayfilm 0102 A4 sheet (5×13, 38.1×21.2 mm, 65 stickers). Print at 100% — do not fit-to-page.

With `store-api` still running:

```
uv run store-tap DEADBEEF
uv run store-tap DEADBEEF --item 4890000000010
uv run store-tap CAFEBABE --item 4890000000010
uv run store-tap CAFEBABE --topup 10
uv run store-enroll AABBCCDD 杏 --yuan 15
```

Empty tap prints the balance. A cart that costs too much prints `need`. `--topup` is yuan.

Kid till (window; pygame-ce extra). Type a barcode and Enter; `A` taps 樂樂, `S` taps 森. Staff: Ctrl+Alt+Shift+P (header turns amber `STAFF` / `PIN`), type PIN `0000`, then F5/F6/F7 top-up, F8 twice reset, F10 void, Esc leave.

```
uv sync --extra kiosk
uv run --extra kiosk store-kiosk
```

Real PC/SC and gun grab wait for the LIFEBOOK. On that laptop set `STORE_DATABASE=/var/lib/store/store.db` and fill `deploy/udev/99-store.rules` from `lsusb`.

Nothing else is installed on the LIFEBOOK until Phase 0. Domain and checkout tests (Phase 1) run here first.

**Kid till (HK 士多, integer 元, pygame-ce):** `shop.py` has no GUI. `kiosk.py` paints it. The LH772 glass is **not a touchscreen** — scan, tap card, or staff keys only. HTML in `prototypes/kid-kiosk/` is only a click-through sketch for the adult’s laptop.

```
pip install -r prototypes/kid-kiosk-pygame/requirements.txt
python prototypes/kid-kiosk-pygame/kiosk.py
```
