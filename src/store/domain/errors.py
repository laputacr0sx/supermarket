class StoreError(Exception):
    """Domain failure. API maps these to HTTP."""


class UnknownCard(StoreError):
    pass


class DuplicateCard(StoreError):
    pass


class InactiveCard(StoreError):
    pass


class StaffCannotShop(StoreError):
    pass


class UnknownProduct(StoreError):
    pass


class ProductNotSellable(StoreError):
    """Draft, inactive, or missing price — checkout must not take money."""


class InsufficientFunds(StoreError):
    def __init__(self, need_cents: int) -> None:
        self.need_cents = need_cents
        super().__init__(f"need {need_cents}")


class InsufficientStock(StoreError):
    pass


class InvalidBarcode(StoreError):
    pass


class InvalidLedger(StoreError):
    pass


class NothingToVoid(StoreError):
    pass


class DuplicateCheckout(StoreError):
    def __init__(self) -> None:
        super().__init__("duplicate checkout")
