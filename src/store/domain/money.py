"""Integer cents in the DB. HK till shows 元 (100 cents = 1 元)."""


def yuan_to_cents(yuan: int) -> int:
    if yuan < 0:
        raise ValueError("yuan must be >= 0")
    return yuan * 100


def cents_to_yuan(cents: int) -> int:
    return cents // 100


def format_yuan(cents: int) -> str:
    return f"{cents_to_yuan(cents)}元"
