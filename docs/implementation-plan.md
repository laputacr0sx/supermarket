# Play supermarket — implementation plan

Locked target: one **Fujitsu LIFEBOOK LH772** (16 GB RAM, SSD) is the store brain. It runs a **Linux kiosk**. Children see a checkout screen and hear beeps. Parents top up cards from the laptop keyboard (staff-unlocked) or from a phone on the LAN. Money lives in SQLite. NFC cards carry only a UID.

This document is the build contract. Implement in the phase order at the end. Do not skip the input-device split or the staff-unlock gate.

---

## 1. Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Brain | LH772, 16 GB, SSD. No Raspberry Pi in v1 | USB host, speakers, 1366×768 panel, keyboard already exist |
| OS | Ubuntu 24.04 LTS *or* Debian 13, minimal + kiosk packages | Long support; Ivy Bridge `i915` is still fine |
| Compositor | **Cage** (Wayland, one app) with **Openbox/X11 fallback** | Cage hides the desktop. HD 4000 can flake on Wayland; keep a tested X11 profile |
| App language | Python 3.12 | FastAPI, evdev, pyscard, ESC/POS, pygame all fit |
| UI toolkit | **pygame-ce** (`import pygame`) fullscreen 1366×768, `SCALED` | This till is a game screen (one surface, huge 元, photos, beeps), not a form app. Qt is heavier than the LH772 needs; admin already lives in phone HTML |
| Glass | **Not a touchscreen.** Cursor hidden. No on-screen buttons | LH772 panel is display only. Kids scan and tap. Staff use the laptop keyboard. Poking the glass does nothing |
| Persistence | SQLite 3, WAL, integer **cents**, Alembic migrations | One file, transactional checkout, no server to babysit |
| Cards | NTAG213 (or any ISO 14443-A). Store **UID only** | Kids with phones cannot rewrite the bank |
| Scanner | USB HID 2D, keyboard wedge | No vendor SDK |
| NFC | ACS ACR1552U via **PC/SC + pyscard**, or PN532 USB as alternate driver | ACR122U is EOL and often fake |
| Admin | FastAPI HTML on LAN, HTTP basic auth. `/docs` off in production | Child never sees a dashboard |
| Staff keys | Dead until staff unlock. Queue amount, apply on next **child** tap | F6 = +$10 with no gate is not playable |
| Money rule | One DB transaction per checkout/top-up. Debounce identical UID 2 s | No double-charge, no torn balances |
| Barcodes | One EAN-13 (or EAN-8) per SKU. Household packs keep their factory code. Shop/toy codes are **random** GS1 restricted-circulation EAN-13s (`200–299`), never sequential | Sequential `200000000001`, `…002` looks fake. Random + check digit looks like a real shop. Same scanner path for cereal and wooden fruit |
| New SKU | Valid unknown scan **learns a draft** on the till. Adult finishes name / price / photo on the phone | Fast pantry raids. Kids are not pricing goods. Drafts are not sellable |
| Labels v1 | A4 PDF, kids cut and tape. 58 mm ESC/POS is Phase 7 *if* they stay into it | A thermal printer is bulky and optional theatre. The number is the product; the printer is not |

---

## 2. Hardware map

Leave this plugged in and do not rearrange ports after udev rules are written.

```
LH772
 ├── LCD 1366×768     kid checkout only (not a touchscreen; dim 20–40%)
 ├── keyboard         staff overlay only
 ├── speakers         beep / paid / nope
 ├── webcam           disable in BIOS or blacklist uvcvideo
 ├── USB-1            HID 2D scanner
 ├── USB-2            ACR1552U or PN532
 ├── USB-3            58 mm ESC/POS printer (optional, Phase 7)
 └── USB-4            spare / powered hub if the printer browns out
```

A normal household printer on the LAN (or USB to a parent laptop) is enough for v1 labels. See §6.2.4. Do not block play on a thermal printer.

### 2.1 Devices to buy (if not already on the desk)

| Role | Model class | Notes |
|---|---|---|
| Scanner | Eyoyo / Netum / Inateck USB HID 2D | Wired. Confirm it types digits + Enter in a text editor |
| NFC | ACS ACR1552U, or Elechouse PN532 USB | Skip RC522. Skip random “ACR122U” clones |
| Cards | NTAG213 white PVC, 10–50 pcs | Label with child names in marker. UID is the identity |
| Labels v1 | Any A4 inkjet/laser + paper or cardstock | Admin prints a PDF grid. Kids cut and tape. See §6.2.4 |
| Printer | USB 58 mm ESC/POS (ZJ-58 class) | **Optional.** Buy only if receipts become the hook. Same EAN-13, different render |
| Hub | Powered USB 3 hub | Only if the printer resets the bus |

### 2.2 Physical child-safety

- Opaque wooden surround if possible: screen + NFC pad toward the child; keyboard and USB dongles toward the adult.
- Tape **status** LEDs (power, HDD, radio, caps). The panel itself is the product display — dim it, do not cover it.
- Cover the webcam.
- On AC power for play sessions. Battery is a UPS, not the plan.
- Lid: `HandleLidSwitch=ignore` so a bump does not suspend the till.

### 2.3 First-boot hardware checklist

On the installed Linux box, before writing app code:

```bash
lsusb
ls -l /dev/input/by-id/
pcsc_scan          # after pcscd is installed; tap a card
aplay /usr/share/sounds/alsa/Front_Center.wav
```

Record vendor/product IDs and `by-id` names into `config/default.toml`. Those strings become udev rules. Do not hard-code `/dev/input/eventN`.

---

## 3. Operating system and kiosk shell

### 3.1 Users

| User | Login | Role |
|---|---|---|
| `pos` | autologin on tty1 into Cage only | Runs the till. No sudo. Groups: `input`, `audio`, `plugdev`, `dialout` |
| `felix` (or `admin`) | SSH only, sudo | You. Never autologin on the console |

Disable guest accounts. Disable GNOME/KDE entirely. This is not a desktop.

### 3.2 Packages (Ubuntu 24.04 names; Debian is the same family)

```
cage seatd greetd          # or the Openbox fallback set
python3.12 python3.12-venv python3-pip
pcscd pcsc-tools libpcsclite-dev
libasound2-dev
libsdl2-2.0-0
fonts-noto-cjk-extra       # 士多 CJK; pygame.freetype loads Noto Sans CJK
sqlite3
git curl
```

Fallback profile extra: `xorg openbox unclutter xdotool lightdm`.

### 3.3 Cage primary (one visible process)

Cage runs a single maximized client and keeps the child inside it.

```
systemd: cage@tty1.service
  User=pos
  PAMName=cage
  ExecStart=/usr/bin/cage -- /opt/store/venv/bin/store-kiosk
  Restart=always
```

If HD 4000 gives a black screen, install `xwayland` first. If it still fails, switch the unit to the Openbox profile. The Python app does not change.

### 3.4 Openbox fallback

LightDM autologin `pos` → Openbox session whose only startup is `store-kiosk --fullscreen`. Openbox rc.xml: no menu, no keybinds for terminals, `A-F4` unbound. `unclutter -idle 0`.

### 3.5 Lockdown

- Mask `getty@tty1` when Cage owns tty1.
- `logind.conf`: `HandleLidSwitch=ignore`, `IdleAction=ignore`.
- `kernel.sysrq = 0` (or a tight mask). You recover over SSH.
- Blacklist `uvcvideo` if the webcam cannot be disabled in BIOS.
- Do not install a browser on the `pos` user.
- Unattended upgrades: security only, `Automatic-Reboot "false"`. Reboot yourself between play days.
- NTP on (`systemd-timesyncd`) so sale timestamps are sane.
- Hostname `store.local` via Avahi so the phone can open `http://store.local:8788`.

### 3.6 Brightness and LEDs

```bash
# persist a dim panel
echo 40 | sudo tee /sys/class/backlight/*/brightness
```

Fujitsu status LEDs are mostly firmware. Tape them. Keyboard backlight off.

---

## 4. Process architecture

Two long-lived processes. One database file.

```
                    ┌──────────────────────────────┐
   phone (LAN) ────►│ store-api :8788  (admin HTML)│
                    │           :8787  (localhost) │
                    │ FastAPI + SQLAlchemy + SQLite│
                    └────────────▲─────────────────┘
                                 │ httpx2 127.0.0.1:8787
                    ┌────────────┴─────────────────┐
   Cage ───────────►│ store-kiosk                  │
                    │  ui/     pygame ViewModel    │
                    │  io/     evdev + pcsc + aplay│
                    └──────────────────────────────┘
                           ▲        ▲        ▲
                      scanner    laptop    NFC pad
                                 keyboard
```

| Process | Unit | Binds | Restarts |
|---|---|---|---|
| `store-api` | `store-api.service` (system) | `127.0.0.1:8787` POS, `0.0.0.0:8788` admin | always |
| `store-kiosk` | started by Cage / Openbox as `pos` | none | Cage `Restart=always` |

`store-api` is the only writer of money. The kiosk is a client. The phone is a client. Tests are a client.

Admin listen address is the LAN. POS listen address is localhost only. FastAPI `docs_url=None` on the production settings profile.

Use FastAPI **lifespan** to open the engine, `PRAGMA journal_mode=WAL`, run Alembic to head, and dispose on shutdown. Routers are included with prefix and dependencies ([FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events), [include_router](https://fastapi.tiangolo.com/reference/apirouter)).

---

## 5. Repository layout

```
supermarket/
  README.md
  docs/implementation-plan.md          ← this file
  pyproject.toml
  alembic.ini
  alembic/versions/
  config/default.toml
  config/devices.example.toml
  deploy/
    bootstrap.sh                       # packages, users, venv, units
    udev/99-store.rules
    systemd/store-api.service
    systemd/cage@.service
    systemd/logind-store.conf
    cage/cage.pam
    openbox/autostart
    openbox/rc.xml
    avahi/store.service
  sounds/                              # wav: beep, paid, nope, staff
  assets/products/                     # optional png, keyed by sku
  src/store/
    __init__.py
    config.py                          # load toml, env overrides
    domain/
      models.py                        # dataclasses / value objects
      errors.py                        # InsufficientFunds, UnknownCard, ...
      money.py                         # cents helpers, format
      barcode.py                       # normalize, check digit, mint, classify
    persist/
      engine.py                        # WAL, BEGIN IMMEDIATE
      tables.py                        # SQLAlchemy 2.0 mapped classes
      repo.py                          # queries only
    services/
      catalog.py                       # lookup, learn-draft, finish, mint
      labels.py                        # A4 PDF of EAN-13s; ESC/POS later
      ledger.py                        # topup, reset, void
      checkout.py                      # the transactional heart
    api/
      app.py                           # FastAPI factory + lifespan
      deps.py                          # SessionDep, admin auth
      routes_pos.py                    # used by kiosk
      routes_admin.py                  # used by phone
      templates/                       # Jinja + HTMX admin
      static/
    io/
      devices.py                       # resolve udev paths
      scanner.py                       # evdev grab → Barcode(str)
      keyboard.py                      # evdev → StaffKey
      nfc.py                           # pcsc monitor → Uid(str)
      printer.py                       # escpos, no-op if missing
      audio.py                         # aplay wrappers
    ui/
      kiosk.py                         # pygame display loop, SCALED / FULLSCREEN
      draw.py                          # paint ViewModel only
      theme.py                         # 1366×768, 元 type, CJK font, colours
    kiosk/
      main.py                          # asyncio loop: io + ui + api client
      fsm.py                           # POS state machine
      client.py                        # httpx2 to store-api
  tests/
    test_checkout.py
    test_ledger.py
    test_fsm.py
    test_barcode.py
    test_labels.py
    test_scanner_decode.py
    test_api.py
  prototypes/
    kid-kiosk/                       # throwaway HTML 士多
    kid-kiosk-pygame/                # locked till: ViewModel + pygame-ce
```

Console scripts in `pyproject.toml`:

- `store-api` → `store.api.app:run`
- `store-kiosk` → `store.kiosk.main:run`
- `store-doctor` → prints devices, pcsc, speaker, DB path (run this on the laptop after every hardware change)

Dependencies (pin in lock file later):

`fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`, `pydantic-settings`, `httpx2`, `evdev`, `pyscard`, `python-escpos` (optional extra), `python-barcode`, `reportlab`, `pygame-ce`, `jinja2`, `python-multipart`, `tomli` (if <3.11), `pytest`, `pytest-asyncio`.

---

## 6. Domain and schema

All amounts are `INTEGER` cents. Never `REAL` for money.

```sql
-- alembic revision 0001

CREATE TABLE products (
  id            INTEGER PRIMARY KEY,
  barcode       TEXT NOT NULL UNIQUE,    -- always normalized (see §6.2)
  origin        TEXT NOT NULL DEFAULT 'household'
                CHECK (origin IN ('household','store')),
  status        TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','ready')),
  name          TEXT,                    -- required before ready
  price_cents   INTEGER CHECK (price_cents IS NULL OR price_cents >= 0),
  stock         INTEGER,                 -- NULL = unlimited
  image_path    TEXT,
  active        INTEGER NOT NULL DEFAULT 1,  -- 0 = taken off the shelf
  created_at    TEXT NOT NULL,           -- UTC ISO-8601
  CHECK (
    status != 'ready'
    OR (name IS NOT NULL AND length(trim(name)) > 0 AND price_cents IS NOT NULL)
  )
);

CREATE TABLE cards (
  id            INTEGER PRIMARY KEY,
  uid           TEXT NOT NULL UNIQUE,    -- hex uppercase, no separators
  child_name    TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'child'  -- child | staff
                CHECK (role IN ('child','staff')),
  active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE accounts (
  card_id       INTEGER PRIMARY KEY REFERENCES cards(id),
  balance_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sales (
  id            INTEGER PRIMARY KEY,
  card_id       INTEGER NOT NULL REFERENCES cards(id),
  total_cents   INTEGER NOT NULL,
  created_at    TEXT NOT NULL,           -- UTC ISO-8601
  voided_at     TEXT
);

CREATE TABLE line_items (
  id            INTEGER PRIMARY KEY,
  sale_id       INTEGER NOT NULL REFERENCES sales(id),
  product_id    INTEGER NOT NULL REFERENCES products(id),
  qty           INTEGER NOT NULL CHECK (qty > 0),
  unit_price_cents INTEGER NOT NULL
);

CREATE TABLE ledger (
  id            INTEGER PRIMARY KEY,
  card_id       INTEGER NOT NULL REFERENCES cards(id),
  kind          TEXT NOT NULL CHECK (kind IN ('topup','reset','void_refund','checkout')),
  amount_cents  INTEGER NOT NULL,        -- signed: checkout negative
  sale_id       INTEGER REFERENCES sales(id),
  created_at    TEXT NOT NULL,
  note          TEXT
);
```

Indexes: `sales(created_at)`, `ledger(card_id, created_at)`, `products(active)`, `products(status)`, `products(origin)`.

Checkout may sell a row only when `status = 'ready' AND active = 1`. Drafts exist so a scan can persist a code before anyone names or prices it.

### 6.2 Barcodes

One symbology at the till: **EAN-13** (UPC-A is the same number with a leading zero). EAN-8 is accepted when a small pack already has one. We do not invent a toy-only Code 128 format. Factory cereal and a taped shop label are the same beep.

#### 6.2.1 Normalize and validate (`domain/barcode.py`)

Every scan and every admin save runs through the same functions.

```
normalize(raw) -> digits
  strip spaces / dashes
  if 12 digits: prepend 0          # UPC-A → EAN-13; check digit unchanged
  if 8 or 13 digits: keep
  else: still return the digit string (caller decides)

ean13_check(body12) -> one digit   # standard 1/3 weighted modulo 10
ean8_check(body7)  -> one digit

classify(normalized) ->
  valid_ean13 | valid_ean8 | invalid
```

`valid_*` means length and check digit match. ISBN-13 (`978…` / `979…`) is already EAN-13.

Invalid / non-GTIN (a QR URL if the gun is misconfigured, a random Code 128) is **never** inserted. Flash “unknown”.

Program the scanner once (Phase 0):

- EAN-13, UPC-A, EAN-8 on; **transmit check digit**
- Convert UPC-A → EAN-13 if the gun has that option
- **QR and Data Matrix off** so a URL on a box does not hit the cart

#### 6.2.2 Household vs shop origin

| Origin | How the code appears | `origin` |
|---|---|---|
| Household pack | Already printed (cereal, toothpaste, a boxed game) | `household` |
| Shop / toy / bin | We minted it and printed a label | `store` |

A boxed toy that already has an EAN-13 is household. Mint only when there is no factory code.

Price is **never** encoded in the number. Price lives in SQLite.

#### 6.2.3 Mint shop codes — random, not sequential

Sequential `200000000001`, `200000000002` looks like a toy cash register. Real EAN-13s look scrambled because the company prefix and item reference are not a counter from 1.

Shop codes use GS1 **restricted circulation** prefixes `200–299` (in-store / regional RCN). They will not collide with factory GS1 on household goods.

```
mint_store_ean13(existing: set[str]) -> str
  retry:
    prefix = random 200..299          # 3 digits, not always 200
    item   = random 000000000..999999999
    body   = f"{prefix:03d}{item:09d}"   # 12 digits
    code   = body + ean13_check(body)
  until code not in existing and not in products.barcode
```

Use `secrets.randbelow` (or `random.SystemRandom`). This is about looking real, not cryptography. Birthday-paradox collision in a 10¹¹ space for a few hundred toys is ignored; the UNIQUE constraint is the backstop.

Do **not** use prefix `02` / variable-measure layouts. Those encode price. We do not.

`origin = 'store'` only on rows we minted. A learned scan of a real bakery `2…` label is still `household`.

#### 6.2.4 Labels: A4 first, thermal later

The identity is the number in SQLite. Rendering is a view.

**v1 (required, Phase 6):** A4 PDF from `services/labels.py`.

- Button: **Print a sheet** (default 24 = 3×8 on A4)
- Mints 24 new random shop codes as `status=draft`, `origin=store`, no name, no price
- Each cell: EAN-13 bars (magnification ≥ 80% of GS1 nominal), human-readable digits, dashed cut marks, a blank write-in line for a pencil name
- Black on white, quiet zones respected. Cardstock if you have it; plain paper is fine
- Kids **cut and tape** onto toys, bins, or shelf edges. Wide tape over the whole label survives sticky fingers
- **Reprint** selected existing shop codes (same numbers, new PDF). Does not mint
- Test-print one page in Phase 2/6 and scan every cell with the gun before a play day

This is the intended craft loop, not a compromise. Cutting and taping *is* stocking the shop.

**Later (Phase 7, optional):** the same `barcode` string on 58 mm ESC/POS. Buy that printer only if receipts become the hook. Missing `/dev/usb/lp0` stays a successful no-op.

#### 6.2.5 Learn-on-scan (kiosk add SKU)

The kiosk does **not** ask for a name or a price. A valid unknown code becomes a draft; an adult finishes it on the phone.

`POST /pos/scan {barcode}` is the only scan call. It normalizes first.

| Situation | DB | HTTP | Kiosk |
|---|---|---|---|
| Ready + active | unchanged | 200 `{action: "sell", product}` | add cart line, `beep.wav` |
| Ready + inactive | unchanged | 200 `{action: "inactive", product}` | flash “not for sale”, keep cart |
| Draft (any origin) | unchanged | 200 `{action: "pending", product}` | “Ask a grown-up”, 2 s, **do not** add to cart |
| Unknown + valid EAN-13/8 | INSERT draft, `origin=household` | 201 `{action: "learned", product}` | “Saved for a grown-up”, 2 s, cart unchanged |
| Unknown + invalid | nothing | 422 `{action: "reject"}` | flash “unknown” 1 s, `nope.wav` |

Dedup: the same unknown code scanned ten times is one draft. `learn_on_unknown` in config (default `true`) can turn the INSERT off if the catalog fills with junk; reject then behaves like invalid.

Kid mode may learn. Staff unlock is for **money**, not for SKUs. Checkout still refuses drafts (`status != 'ready'` → treat as unknown sku, leave balance alone).

Admin on `:8788`:

- **Unfinished** list first (drafts), then the shelf (ready)
- Open a draft: name, price (dollars in the form), optional photo (`<input type="file" accept="image/*" capture="environment">`), save → `status=ready`
- Photo lands in `/var/lib/store/images/{id}.jpg`. The kiosk shows it once the item is ready
- Manual type-in of a household EAN is still allowed (pack is in the kitchen)
- Deactivate / delete unused drafts (printed but never stuck on anything)

Play-day loop:

1. Print a sheet of 24 shop codes. Kids cut, tape, write a pencil name.
2. Raid the pantry: scan real packs. Each valid new EAN becomes a draft.
3. Sit with the phone: pick each unfinished row, photo + price + proper name.
4. After that, those scans beep and sell.

### 6.1 SQLite engine rules

On every connect:

```
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

Checkout and ledger writes use an explicit transaction that starts with **`BEGIN IMMEDIATE`** so two taps cannot interleave. SQLAlchemy 2.0: listen on `connect` / `begin` and emit `BEGIN IMMEDIATE` yourself ([SQLite dialect notes](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)). Then:

```python
with Session(engine) as session:
    with session.begin():
        # SELECT account ...  (row is reserved by IMMEDIATE)
        # check, insert sale + lines + ledger, update balance
```

File path: `/var/lib/store/store.db` owned by a `store` system user that `store-api` runs as. Daily copy to `/var/backups/store/store-YYYYMMDD.db` via a timer.

---

## 7. HTTP API

Base: `http://127.0.0.1:8787` (kiosk). Admin HTML + same JSON under `http://<lan>:8788` with HTTP basic auth.

### 7.1 POS (no auth, localhost only)

| Method | Path | Body | Result |
|---|---|---|---|
| POST | `/pos/scan` | `{barcode}` | 200/201 `{action, product?}` or 422 (see §6.2.5). Path param is **not** used; the body is normalized server-side |
| GET | `/pos/products/{barcode}` | | 200 product (incl. `status`) or 404. Lookup only; does **not** learn |
| POST | `/pos/checkout` | `{uid, items:[{barcode, qty}]}` | 200 `{sale_id, total_cents, balance_cents}` or 402 `{need_cents}` or 404 card/product. Draft or inactive barcode → 404 |
| GET | `/pos/cards/{uid}` | | 200 `{name, role, balance_cents, active}` or 404 |
| POST | `/pos/ledger` | `{uid, kind, amount_cents?}` | staff-only semantics; kiosk may call only after local staff unlock |
| POST | `/pos/void-last` | `{uid?}` | voids most recent non-voided sale |

`/pos/ledger` kinds:

- `topup` requires `amount_cents > 0`
- `reset` sets balance to 0 (ledger row records the negative delta)
- kiosk must not expose these without the FSM being in `staff`

Idempotency: accept optional `Idempotency-Key`. Replay of the same key within 30 s returns the original result. Also reject a second checkout for the same UID within 2 s.

### 7.2 Admin (basic auth, LAN)

HTML first (HTMX). JSON is fine for later.

- **Unfinished drafts** first; finish name / price / photo; then list / edit / deactivate ready products
- **Print a sheet**: mint N random shop EAN-13s + download A4 PDF. Reprint selected codes without minting
- Type a household barcode by hand if the pack is not at the till
- Enroll card: tap on the till *or* type UID, set child name, optional opening balance
- Mark card staff vs child
- Top up / reset (same service as POS ledger)
- Void last sale
- Sales log for today
- “Doctor” page: API up, DB path, last backup

Do not ship `/docs` or `/redoc` on `:8788`.

---

## 8. POS state machine

This is the product. Implement `store.kiosk.fsm` as a pure function so tests do not need pygame or USB.

```
          barcode (sell)
   ┌─────────────┐
   │    idle     │──────────────► cart
   └──────▲──────┘                 │  barcode sell: add line
          │                        │  barcode pending/learned: result 2s, keep/return
          │ timeout 5 min          │  barcode reject: flash 1s, keep
          │ or clear               │  NFC child + cart: checkout
          │                        │  NFC child + empty: show balance (result 2s)
          │                        │  staff unlock: staff
          │                        ▼
          │                      result ──3s──► idle or cart (if 402 or still in cart)
          │
   staff unlock (staff UID or Ctrl+Alt+Shift+P + PIN)
          ▼
        staff ── F5/F6/F7/F8/F9 ──► staff_queued ── child tap ──► result ──► idle
          │                              │
          └── Esc / timeout 30s ─────────┘
```

A learn or pending scan must **not** clear the cart. It is a 2 s overlay, then back to idle or cart.

### 8.1 Events

```
Barcode(code: str)
Uid(uid: str)
Key(name: str)            # F5, F6, Escape, Digit, Enter, ...
Tick(now)
ApiResult(...)
```

### 8.2 Staff key map (live only in `staff` / `staff_queued`)

| Key | Queue |
|---|---|
| F5 | topup +500 cents |
| F6 | topup +1000 |
| F7 | topup +2000 |
| F8 | reset to 0 (require a second F8 to confirm) |
| F9 | enter custom amount (digits + Enter) |
| F10 | void last sale (no card tap; confirm) |
| Esc | cancel queue / leave staff if nothing queued |

In `idle` / `cart` / `result`, **all of the above are ignored**. Digit keys from the **laptop** do nothing in kid mode. Digits from the **scanner** are not keys; they are assembled in `scanner.py` into a `Barcode`.

### 8.3 Checkout outcome → UI + audio

| Outcome | Screen | Sound |
|---|---|---|
| line added | last item + fat total | `beep.wav` |
| learned draft | “Saved” + last 4 digits | `staff.wav` (soft) |
| pending draft | “Ask a grown-up” | `staff.wav` (soft) |
| unknown / invalid | flash “unknown” 1 s, keep cart | `nope.wav` |
| paid | “Paid $X — Alex has $Y” | `paid.wav` + optional print |
| 402 | “Need $X more” | `nope.wav`, keep cart |
| unknown / inactive card | “Not our card” | `nope.wav` |
| staff ready | thin amber bar `STAFF` | `staff.wav` (soft) |
| topup applied | “+$10 for Alex” | `paid.wav` |

---

## 9. I/O drivers

All drivers expose an `async` iterator of domain events. `kiosk.main` merges them with `asyncio.Queue`.

### 9.1 Scanner (`io/scanner.py`)

- Open `/dev/input/by-id/<configured>` **or** the udev symlink `/dev/input/store-scanner`.
- `device.grab()` so the compositor never sees the barcode ([python-evdev exclusive access](https://python-evdev.readthedocs.io/en/latest/tutorial.html)).
- Translate `EV_KEY` down events through a US-QWERTY map. Accumulate until `KEY_ENTER`. Emit `Barcode`.
- Ignore auto-repeat. Shift handles Code128 that includes letters (we still reject those unless they normalize to a valid EAN).
- If the device disappears, log, sleep 1 s, rescan `by-id`. USB unplug/replug must self-heal.
- After `lsusb`, program the gun: EAN-13 / UPC-A / EAN-8 on, check digit on, QR/Data Matrix off. Record that in the runbook.

### 9.2 Laptop keyboard (`io/keyboard.py`)

- Open the Fujitsu keyboard by `by-id` (the one that is **not** the scanner).
- Do **not** grab it unless you also want to swallow brightness keys. Prefer: Cage already sends keys only to the kiosk; pygame ignores text entry in kid states; `keyboard.py` is the only decoder for F-keys and the PIN chord.
- Chord `Ctrl+Alt+Shift+P` starts PIN entry (4 digits). Compare to `bcrypt` hash in config. Success → `StaffUnlock`.
- Never treat scanner digits as PIN.

### 9.3 NFC (`io/nfc.py`)

PC/SC path (ACR1552U):

```
pcscd  →  pyscard SCardGetStatusChange  →  ATR + UID
```

UID: uppercase hex, no colons, 8 or 14 hex chars typical for NTAG. Debounce: same UID within 2 s is one tap.

PN532 path is a second adapter behind the same `NfcMonitor` protocol so the FSM does not care.

Staff vs child is **not** on the chip. It is `cards.role` in SQLite.

### 9.4 udev (`deploy/udev/99-store.rules`)

After `lsusb` / `by-id` are known:

```
# Scanner: hide from libinput so Cage/pygame cannot type the barcode
SUBSYSTEM=="input", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", \
  ENV{ID_INPUT_KEYBOARD}="0", ENV{LIBINPUT_IGNORE_DEVICE}="1", \
  SYMLINK+="input/store-scanner", GROUP="input", MODE="0660"

# NFC USB device node (if not only PC/SC)
SUBSYSTEM=="usb", ATTR{idVendor}=="072f", MODE="0660", GROUP="plugdev"
```

`store-doctor` must print whether `LIBINPUT_IGNORE_DEVICE` is set.

### 9.5 Audio and printer

- `audio.py` calls `aplay` on the default ALSA/PipeWire sink. Missing file = log, do not crash.
- `printer.py` uses `python-escpos`. If `/dev/usb/lp0` is absent, it is a successful no-op. Receipt: store name, lines, total, remaining balance, time. Shop labels in v1 are **not** this device — they are the A4 PDF in `labels.py`.

---

## 10. Kid UI (pygame-ce)

This till is a **game screen**, not a desktop app. pygame-ce (`import pygame`) is the locked toolkit:

- One 1366×768 surface, `SCALED` + `FULLSCREEN`, **cursor always hidden**
- The panel is not a touchscreen. No hit targets, no on-glass buttons, no swipe, no on-screen keypad. Mouse clicks are ignored
- Inputs: HID scanner → `Barcode`, NFC → `Uid`, laptop keyboard → staff keys only (after unlock)
- Huge integer **元**, product JPEGs, beeps — SDL’s job
- Ivy Bridge + Cage: no Qt runtime, no widget tree, no stylesheet engine
- Phone admin stays FastAPI + HTMX. The till never grows forms

Official `pygame` is the same API if a distro wheel is easier; **pygame-ce** is what we develop against (cp314 wheels today; 3.12 on the LH772).

The till draws an immutable **ViewModel** (header, picture, item 元, title, 共/差/剩). FSM / catalog never import pygame. Reference implementation: `prototypes/kid-kiosk-pygame/` (`shop.py` + `kiosk.py`). Production copies that split into `src/store/ui/`.

Four visual regions only:

1. Header: store name (idle) or amber `STAFF` bar
2. Hero: product image / card icon / result glyph
3. **Item 元** (dominant) then a short name
4. **共 / 差 / 剩** + integer 港元 (largest type)

Theme: high contrast, no settings gear, no hamburger, nothing that looks tappable. HK copy stays fewest Traditional characters (`士多`, `掃嘢`, `拍卡`, `得`, `唔夠`). CJK via `pygame.freetype` + Noto Sans CJK (or 微軟正黑體 on a Windows laptop). Product photos optional; a tile is enough for v1.

`ui/draw.py` receives the ViewModel. It does not call the API. That keeps pygame out of the money path.

---

## 11. Admin on the phone

`store-api` serves Jinja + HTMX on `:8788`.

- Big buttons: +$5 / +$10 / +$20 / set $0 / enroll
- **Unfinished** drafts (from pantry scans and from printed sheets). Finish: name, price, phone camera photo
- Product form: barcode (read-only once learned), name, price (dollars in the form, cents in the DB)
- **Print a sheet** / reprint → A4 PDF download
- Basic auth: `admin` + a long password in `/etc/store/config.toml` (file mode `0640`, group `store`)
- Bound to LAN. Firewall: allow `8788/tcp` from `192.168.0.0/16` and `10.0.0.0/8` only. Do not port-forward.

The kiosk never links to this UI.

---

## 12. Configuration

`/etc/store/config.toml` (production) overlays `config/default.toml` (repo).

```toml
[store]
name = "Corner Shop"
currency = "USD"
locale = "en_US"

[paths]
database = "/var/lib/store/store.db"
sounds = "/opt/store/sounds"
product_images = "/var/lib/store/images"

[net]
pos_host = "127.0.0.1"
pos_port = 8787
admin_host = "0.0.0.0"
admin_port = 8788
docs = false

[auth]
admin_user = "admin"
admin_password_hash = "$2b$..."   # bcrypt
staff_pin_hash = "$2b$..."

[devices]
scanner = "/dev/input/store-scanner"
keyboard = "/dev/input/by-id/usb-Fujitsu-event-kbd"  # fill via store-doctor
nfc = "pcsc"
printer = "/dev/usb/lp0"

[play]
cart_idle_clear_s = 300
staff_timeout_s = 30
uid_debounce_s = 2
result_hold_s = 3
backlight = 40

[catalog]
learn_on_unknown = true
store_prefix_min = 200
store_prefix_max = 299
label_rows = 8
label_cols = 3
```

Environment overrides for tests: `STORE_DATABASE=:memory:`, `STORE_DOCS=true`.

---

## 13. Coding rules

- Domain and FSM have **no** pygame, evdev, or FastAPI imports. That is what makes the till testable on Windows while you wait for USB hardware.
- Services take a `Session` and return values or raise `domain.errors`.
- API layer maps errors to HTTP (402, 404, 409).
- Kiosk maps errors to `ViewModel` + sound.
- One writer process for SQLite (`store-api`). Kiosk never opens the DB file.
- Logging: structlog or stdlib JSON to journald. Never log full card UIDs in info; last 4 hex is enough.
- Format: Ruff + pytest in CI later. For now, `pytest` must pass on every phase that adds logic.

---

## 14. Tests (write with the phase, not after)

| Area | Cases |
|---|---|
| `checkout` | happy path; insufficient funds leaves balance and stock unchanged; unknown card; unknown sku; **draft sku is not sold**; double tap same key is one sale |
| `ledger` | topup; reset writes a negative delta; inactive card rejected; staff card has no shopper balance checkout |
| `barcode` | UPC-A pads to EAN-13; check digit vectors; invalid rejected; mint stays in 200–299, is unique, is **not** sequential; same raw forms collide after normalize |
| `catalog` | valid unknown → one draft; second scan of that code is pending not a second row; invalid inserts nothing; finish without name/price stays draft |
| `labels` | A4 3×8 PDF contains exactly the minted codes as digits; reprint does not mint |
| `fsm` | F6 in idle is ignored; staff unlock then F6 then child tap emits `LedgerRequest`; cart timeout clears; 402 keeps cart; learn/pending does not clear cart |
| `scanner` decode | fixture of evdev-like key names → barcode string |
| `api` | TestClient against in-memory SQLite |

No hardware in CI. `store-doctor` is the hardware test, run by hand on the LH772.

---

## 15. Deploy units (sketch)

`store-api.service`:

```
[Service]
User=store
Group=store
WorkingDirectory=/opt/store
ExecStart=/opt/store/venv/bin/store-api
Restart=always
RestartSec=1
```

Cage unit follows the [upstream systemd recipe](https://github.com/cage-kiosk/cage/wiki/Starting-Cage-on-boot-with-systemd): `Conflicts=getty@%i.service`, `PAMName=cage`, `StandardInput=tty-fail`, `Restart=always`. After first successful graphical start, add `ExecStartPost` to `chvt` the kiosk tty.

`bootstrap.sh` (you run once over SSH):

1. Create users `store`, `pos`
2. Install packages
3. `python3.12 -m venv /opt/store/venv` and install the project
4. Install udev, systemd, Avahi, logind drop-in
5. `alembic upgrade head`
6. Seed two products and one staff card + one child card
7. Enable `store-api` and `cage@tty1`
8. Reboot, run `store-doctor`

---

## 16. Implementation phases

Build in this order. Each phase is playable or proves a risk. Do not start UI theming before checkout is transactional.

### Phase 0 — Bring-up (laptop)

- Ubuntu 24.04 or Debian 13, SSD confirmed, 16 GB seen by `free -h`
- Users, SSH, `store-doctor` stub that lists `lsusb` and `/dev/input/by-id`
- Decide Cage vs Openbox by actually launching `cage -- foot` (or `xterm`). If black screen: Xwayland, then Openbox
- Record scanner and keyboard `by-id` into `config/devices.example.toml`

**Done when:** after reboot you get a single full-screen terminal as `pos`, and SSH still works as admin.

### Phase 1 — API + schema

- `pyproject.toml`, Alembic 0001, WAL engine, FastAPI factory + lifespan
- `domain/barcode.py` + catalog learn/finish/mint + checkout and ledger + pytest
- Seed script (one ready household SKU is enough)

**Done when:** `pytest` passes on the LH772 and on your Windows machine, including mint uniqueness and “draft cannot be sold”.

### Phase 2 — Scanner path

- udev hide-from-libinput + `grab()`
- Program the gun (EAN-13 / check digit / no QR)
- CLI: `POST /pos/scan` — ready cereal prints the name; a new valid pack inserts a draft; garbage 422s
- Generate one A4 test PDF on Windows and confirm the gun reads every cell

**Done when:** scanning cereal in a console prints the product, a second unknown valid pack creates one draft row, and the letters do **not** appear in any other window.

### Phase 3 — NFC + checkout

- `pcscd` + `nfc.py`
- Enroll one staff UID and one child UID via a CLI
- Empty-cart tap = balance; cart + tap = checkout
- 402 path

**Done when:** you can overdraw-fail, top up via CLI, then pay.

### Phase 4 — Kiosk UI

- pygame-ce 1366×768, `SCALED` / `FULLSCREEN`, hidden cursor
- Paint the ViewModel from `shop.py` / FSM (promote `prototypes/kid-kiosk-pygame/`)
- Wire httpx2 client + beeps
- CJK font present (`fc-list :lang=zh`)

**Done when:** a child who barely reads still understands 掃 → 拍 → 得 / 唔夠. A pantry scan of something new shows 記低, not a cart line.

### Phase 5 — Staff keyboard

- Chord + PIN, timeouts, F5–F10, double-F8 reset confirm
- Amber staff bar
- Apply on next child tap

**Done when:** mashing the keyboard in kid mode cannot change a balance, and you can add $10 without the phone.

### Phase 6 — Phone admin

- HTMX pages on `:8788`, basic auth, Avahi
- Unfinished drafts, finish (name / price / camera photo), enroll, top-up, today’s sales
- **Print a sheet** / reprint → A4 PDF. Kids cut and tape

**Done when:** you can run a play day without SSH: print labels, scan pantry, finish drafts on the phone, sell.

### Phase 7 — Theatre (optional thermal)

- ESC/POS receipts **if** you bought the 58 mm printer
- Same shop EAN-13 can reprint on the thermal as a single sticker
- Optional wooden surround, taped LEDs, dim preset

Skip this phase entirely if the A4 labels and screen are enough.

### Phase 8 — Hardening

- Backups timer, journald disk cap
- Confirm no `/docs`, no port-forward
- Fail-soft: missing printer, missing speaker, NFC unplug (banner “card reader off”, cart still works)
- One-page runbook: “play day start / end / lost card / replace scanner”

---

## 17. Failure modes (handle these explicitly)

| Fault | Behaviour |
|---|---|
| Scanner unplugged | Banner, rescan loop, cart remains |
| NFC unplugged | Banner, cannot pay or staff-tap; cart remains |
| API down | Kiosk shows “shop asleep”; Cage restarts kiosk; systemd restarts API |
| Disk full | WAL writes fail closed; do not pretend the sale happened |
| Duplicate tap | 2 s debounce + idempotency key |
| Lost child card | Admin: `active=0`, enroll new UID, transfer balance by ledger pair |
| Draft flood | Kids scan the whole house. Admin deletes unused drafts; set `learn_on_unknown = false` if needed |
| Printed sheet, unused | Leave as drafts or delete. Reprint is for codes you still want |
| Power loss mid-commit | SQLite rollback; worst case last sale missing, balance consistent |
| Child finds Ctrl+Alt+F3 | If not locked down, they get a TTY. Phase 0 must disable unused VTs or require login |

---

## 18. What we are not building in v1

- Balance stored on the NFC chip
- Computer-vision auto-checkout
- Multiple tills
- Live GS1 / Open Food Facts name lookup (drafts stay unnamed until an adult types)
- A second toy-only barcode format (no `TOY-001`, no sequential PLUs)
- Price encoded inside the barcode
- e-Ink shelf tags (add as Phase 9 if the game sticks)
- Cloud sync
- Windows kiosk path (Linux only). Domain, PDF labels, and tests **do** run on Windows |

---

## 19. Suggested first code drop

When implementation starts, land Phase 1 as:

1. `pyproject.toml` + package tree
2. `persist/engine.py` + Alembic 0001
3. `domain/barcode.py` + `services/catalog.py` + `services/checkout.py` + `services/ledger.py`
4. `api/app.py` with lifespan, `POST /pos/scan`, and the other POS routes
5. `tests/test_barcode.py` + `tests/test_checkout.py` red → green

Phases 0 and 2 need the physical LH772. Phase 1 does not.
