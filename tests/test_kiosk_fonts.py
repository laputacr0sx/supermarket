from pathlib import Path

from store.kiosk.copy import COPY
from store.kiosk.fonts import KAI_FILENAME, find_cjk_font, find_fallback_font, is_kai


def test_bundled_kai_is_preferred() -> None:
    path = find_cjk_font()
    assert path is not None
    assert Path(path).name == KAI_FILENAME
    assert is_kai(path)


def test_fallback_is_not_the_kai_file() -> None:
    path = find_fallback_font()
    if path is None:
        return
    assert not is_kai(path)


def test_copy_is_written_chinese() -> None:
    assert COPY.store == "士多"
    assert COPY.idle_title == "請掃"
    assert COPY.idle_sub == "拍卡"
    assert COPY.paid == "完成"
    assert COPY.remain == "餘額"
    assert COPY.still_have == "餘額"
    assert COPY.need == "不足"
    assert COPY.learned == "記下"
    assert COPY.unknown == "不識"
    assert COPY.total == "合計"
    assert COPY.empty_cart == "未掃"
    assert COPY.yuan == "元"
    assert COPY.leftover_of("樂樂") == "樂樂 餘額"
    assert COPY.cart_count(2) == "2件"
    assert COPY.cart_count(0, empty=COPY.empty_cart) == "未掃"
