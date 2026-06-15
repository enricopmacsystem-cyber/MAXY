from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings, get_settings


@dataclass(frozen=True)
class EasyOneEndpoints:
    """Path API configurabili — allineare con documentazione Buffetti/EasyOne."""

    auth_login: str = "/authentication/Login"
    auth_refresh: str = "/api/auth/refresh"
    products_search: str = "/api/products/search"
    product_by_code: str = "/api/products/{code}"
    stock_by_code: str = "/api/warehouse/stock/{code}"
    stock_search: str = "/api/warehouse/search"
    customers_search: str = "/people"
    customer_by_code: str = "/people/{code}"
    orders_search: str = "/joborders"
    order_by_number: str = "/joborders/{order_number}"
    tickets_by_event: str = "/tickets/{event_id}"
    events_create: str = "/Event"
    events_basic_info: str = "/event/GetEventBasicInfo/{app_id}"
    calendar_events: str = "/calendar/events"
    documents_by_product: str = "/api/documents/product/{code}"

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "EasyOneEndpoints":
        settings = settings or get_settings()
        return cls(
            auth_login=settings.easyone_path_auth_login,
            auth_refresh=settings.easyone_path_auth_refresh,
            products_search=settings.easyone_path_products_search,
            product_by_code=settings.easyone_path_product_by_code,
            stock_by_code=settings.easyone_path_stock_by_code,
            stock_search=settings.easyone_path_stock_search,
            customers_search=settings.easyone_path_customers_search,
            customer_by_code=settings.easyone_path_customer_by_code,
            orders_search=settings.easyone_path_orders_search,
            order_by_number=settings.easyone_path_order_by_number,
            tickets_by_event=settings.easyone_path_tickets_by_event,
            events_create=settings.easyone_path_events_create,
            events_basic_info=settings.easyone_path_events_basic_info,
            calendar_events=settings.easyone_path_calendar_events,
            documents_by_product=settings.easyone_path_documents_by_product,
        )
