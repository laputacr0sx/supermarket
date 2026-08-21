from store.kiosk.fsm import (
    Barcode,
    Key,
    PayReply,
    ScanReply,
    StaffUnlock,
    Tick,
    Uid,
    idle,
    step,
    view,
)


def _sell(name: str, barcode: str, cents: int) -> ScanReply:
    return ScanReply(
        "sell",
        {"name": name, "barcode": barcode, "price_cents": cents, "image_path": None},
    )


def test_sell_scan_enters_cart_and_keeps_total() -> None:
    state, effect = step(idle(), Barcode("1"), now=0)
    assert effect.kind == "scan"
    state, _ = step(state, _sell("麥片", "1", 1200), now=1)
    vm = view(state)
    assert vm.title == "麥片"
    assert vm.tag_yuan == 12
    assert vm.sum_yuan == 12
    assert vm.sum_label == "共"


def test_learn_does_not_clear_cart() -> None:
    state, _ = step(idle(), Barcode("1"), now=0)
    state, _ = step(state, _sell("麥片", "1", 1200), now=1)
    state, _ = step(state, Barcode("2"), now=2)
    state, _ = step(state, ScanReply("learned", {"barcode": "5901234123457"}), now=3)
    assert state.cart
    assert view(state).title == "記低"
    state, _ = step(state, Tick(), now=6)
    assert view(state).title == "麥片"


def test_empty_tap_asks_for_card() -> None:
    state, effect = step(idle(), Uid("DEADBEEF"), now=0)
    assert effect.kind == "card"


def test_cart_tap_checks_out() -> None:
    state, _ = step(idle(), Barcode("1"), now=0)
    state, _ = step(state, _sell("麥片", "1", 1200), now=1)
    state, effect = step(state, Uid("DEADBEEF"), now=2)
    assert effect.kind == "checkout"
    assert effect.uid == "DEADBEEF"
    paid = PayReply("paid", total_cents=1200, balance_cents=1800, name="樂樂")
    state, _ = step(state, paid, now=3)
    vm = view(state)
    assert vm.title == "得"
    assert vm.sum_label == "剩"
    assert vm.sum_yuan == 18
    assert state.cart == ()


def test_402_keeps_cart() -> None:
    state, _ = step(idle(), Barcode("1"), now=0)
    state, _ = step(state, _sell("麥片", "1", 1200), now=1)
    state, _ = step(state, PayReply("need", need_cents=700, name="森"), now=2)
    assert state.cart
    vm = view(state)
    assert vm.title == "唔夠"
    assert vm.sum_label == "差"
    assert vm.sum_yuan == 7


def test_reject_keeps_cart() -> None:
    state, _ = step(idle(), Barcode("1"), now=0)
    state, _ = step(state, _sell("麥片", "1", 1200), now=1)
    state, _ = step(state, ScanReply("reject", None), now=2)
    assert state.cart
    assert view(state).title == "唔識"


def test_f6_ignored_in_idle() -> None:
    state, effect = step(idle(), Key("F6"), now=0)
    assert effect.kind == "none"
    assert state.mode == "idle"


def test_staff_f6_then_child_tap_emits_ledger() -> None:
    state, _ = step(idle(), StaffUnlock(), now=0)
    assert view(state).header == "STAFF"
    state, _ = step(state, Key("F6"), now=1)
    state, effect = step(state, Uid("DEADBEEF"), now=2)
    assert effect.kind == "ledger"
    assert effect.ledger_kind == "topup"
    assert effect.amount_cents == 1000
    assert effect.uid == "DEADBEEF"


def test_esc_leaves_staff() -> None:
    state, _ = step(idle(), StaffUnlock(), now=0)
    state, _ = step(state, Key("Escape"), now=1)
    assert state.mode == "idle"
    assert view(state).header == "士多"


def test_f8_needs_second_press() -> None:
    state, _ = step(idle(), StaffUnlock(), now=0)
    state, effect = step(state, Key("F8"), now=1)
    assert effect.kind == "none"
    state, effect = step(state, Key("F8"), now=2)
    state, effect = step(state, Uid("DEADBEEF"), now=3)
    assert effect.kind == "ledger"
    assert effect.ledger_kind == "reset"
