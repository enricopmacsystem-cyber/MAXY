from app.schemas.chat import AvailabilityInfo
from app.schemas.product import ProductResponse

LOW_STOCK_THRESHOLD = 10


def availability_info(product: ProductResponse) -> AvailabilityInfo:
    qty = product.availability
    if qty <= 0:
        return AvailabilityInfo(
            quantity=0,
            status="esaurito",
            status_label="Esaurito — verificare riassortimento",
        )
    if qty <= LOW_STOCK_THRESHOLD:
        return AvailabilityInfo(
            quantity=qty,
            status="scorte_basse",
            status_label=f"Scorte basse — {qty} pezzi disponibili",
        )
    return AvailabilityInfo(
        quantity=qty,
        status="disponibile",
        status_label=f"Disponibile — {qty} pezzi a magazzino",
    )
