from decimal import Decimal, ROUND_HALF_UP


def calculate_margin_percent(
    price: Decimal,
    cost_price: Decimal | None,
) -> Decimal | None:
    """Calcola margine % = (prezzo - costo) / prezzo * 100."""
    if cost_price is None or price <= 0:
        return None
    if cost_price > price:
        return Decimal("0.00")
    margin = ((price - cost_price) / price) * Decimal("100")
    return margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
