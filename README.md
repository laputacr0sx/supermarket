# Play supermarket

A Linux kiosk checkout for a toy shop: USB barcode scanner, NFC debit cards, money in SQLite, kid-facing UI on a Fujitsu LIFEBOOK LH772 (16 GB, SSD).

Children scan and tap. Parents top up from a staff-unlocked keyboard or a phone on the LAN. Cards hold a UID only.

Products are EAN-13: real household packs keep their factory code; toys get a **random** in-store EAN-13 on an A4 sheet that kids cut and tape. An unknown valid scan becomes a draft; an adult finishes name, price, and photo on the phone.

**Implementation contract:** [docs/implementation-plan.md](docs/implementation-plan.md)

**Git:** [CONTRIBUTING.md](CONTRIBUTING.md) — `main` stays green; short-lived branches; squash-merge PRs.

That plan locks hardware, OS/kiosk (Cage + Openbox fallback), **pygame-ce** for the kid till, process split (`store-api` / `store-kiosk`), schema, API, state machine, and build phases 0–8.

**Phase 1 (Windows, same tree later copied to the LIFEBOOK):**

```
python -m pip install -e ".[dev]"
python -m pytest
set STORE_DATABASE=data\store.db
store-seed
store-doctor
store-api
```

`store-api` listens on `http://127.0.0.1:8787`. Try `POST /pos/scan` with a seeded barcode. On the laptop set `STORE_DATABASE=/var/lib/store/store.db` — no code change.

Nothing else is installed on the LIFEBOOK until Phase 0. Domain and checkout tests (Phase 1) run here first.

**Kid till (HK 士多, integer 元, pygame-ce):** `shop.py` has no GUI. `kiosk.py` paints it. The LH772 glass is **not a touchscreen** — scan, tap card, or staff keys only. HTML in `prototypes/kid-kiosk/` is only a click-through sketch for the adult’s laptop.

```
pip install -r prototypes/kid-kiosk-pygame/requirements.txt
python prototypes/kid-kiosk-pygame/kiosk.py
```
