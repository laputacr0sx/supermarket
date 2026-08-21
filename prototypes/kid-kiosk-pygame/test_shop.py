"""Pure tests — no pygame. Proves the till ports without a display."""

from shop import Shop, ViewModel
from store.kiosk.copy import COPY


def test_scan_ready_emphasizes_item_and_total():
    shop = Shop()
    assert shop.scan("cereal") == "sell"
    vm = shop.view()
    assert vm.title == "麥片"
    assert vm.tag_yuan == 12
    assert vm.sum_yuan == 12
    assert vm.sum_label == COPY.total
    assert vm.count == "1件"
    assert vm.picture == "cereal"


def test_cart_total_is_integer_yuan():
    shop = Shop()
    shop.scan("cereal")
    shop.scan("milk")
    vm = shop.view()
    assert vm.tag_yuan == 8
    assert vm.title == "牛奶"
    assert vm.sum_yuan == 20


def test_sam_cannot_pay():
    shop = Shop()
    shop.scan("cereal")
    shop.scan("milk")
    assert shop.tap("sam") == "nope"
    vm = shop.view()
    assert vm.title == COPY.need
    assert vm.sum_label == COPY.short
    assert vm.sum_yuan == 15
    assert shop.cart_total() == 20


def test_alex_pays_and_keeps_remainder():
    shop = Shop()
    shop.scan("cereal")
    shop.scan("milk")
    assert shop.tap("alex") == "paid"
    vm = shop.view()
    assert vm.title == COPY.paid
    assert vm.tag_yuan == 20
    assert vm.sum_yuan == 10
    assert vm.sum_label == COPY.remain
    assert shop.cards["alex"].balance == 10
    assert shop.cart == []


def test_unknown_valid_becomes_draft():
    shop = Shop()
    assert shop.scan("toothpaste") == "saved"
    assert shop.view().title == COPY.learned
    assert shop.catalog["toothpaste"].status == "draft"
    assert shop.scan("toothpaste") == "saved"
    assert shop.view().title == COPY.ask_adult


def test_invalid_does_not_insert():
    shop = Shop()
    n = len(shop.drafts)
    assert shop.scan("junk") == "nope"
    assert shop.view().title == COPY.unknown
    assert len(shop.drafts) == n


def test_finish_draft_then_sell():
    shop = Shop()
    assert shop.finish_draft("2718403957618", "蘋果", 3)
    assert shop.scan("apple") == "sell"
    vm = shop.view()
    assert vm.title == "蘋果"
    assert vm.tag_yuan == 3
    assert vm.sum_yuan == 3


def test_result_expires_back_to_cart():
    shop = Shop()
    shop.scan("cereal")
    shop.tap("sam", now_ms=0)
    assert shop.view().title == COPY.need
    shop.tick(5999)
    assert shop.view().title == COPY.need
    shop.tick(6000)
    assert shop.view().title == "麥片"
    assert shop.cart_total() == 12


def test_viewmodel_has_no_html():
    shop = Shop()
    shop.scan("milk")
    vm = shop.view()
    assert isinstance(vm, ViewModel)
    assert "<" not in vm.title
    assert vm.tag_yuan == 8


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all passed")
