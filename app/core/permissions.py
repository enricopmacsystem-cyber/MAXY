from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    PRODUCTS_READ = "products:read"
    WAREHOUSE_READ = "warehouse:read"
    PRICING_READ = "pricing:read"
    PRICING_MARGIN = "pricing:margin"
    CUSTOMERS_READ = "customers:read"
    ORDERS_READ = "orders:read"
    DOCUMENTS_READ = "documents:read"
    AI_CHAT = "ai:chat"
    AI_COPILOT = "ai:copilot"
    MAIL_ACCESS = "mail:access"
    CALENDAR_READ = "calendar:read"
    INTERNAL_CHAT = "internal_chat:access"
    ADMIN_SYNC = "admin:sync"


ALL_SCOPES: frozenset[str] = frozenset(scope.value for scope in Scope)

# Mapping permessi EasyOne → scope MAC AI (da estendere con documentazione vendor)
EASYONE_PERMISSION_MAP: dict[str, str] = {
    "catalogo.lettura": Scope.PRODUCTS_READ,
    "magazzino.lettura": Scope.WAREHOUSE_READ,
    "listini.lettura": Scope.PRICING_READ,
    "listini.margine": Scope.PRICING_MARGIN,
    "clienti.lettura": Scope.CUSTOMERS_READ,
    "ordini.lettura": Scope.ORDERS_READ,
    "documenti.lettura": Scope.DOCUMENTS_READ,
    "ai.chat": Scope.AI_CHAT,
    "ai.copilot": Scope.AI_COPILOT,
    "mail.access": Scope.MAIL_ACCESS,
    "calendar.read": Scope.CALENDAR_READ,
    "chat.interna": Scope.INTERNAL_CHAT,
    "internal_chat.access": Scope.INTERNAL_CHAT,
    "admin.sync": Scope.ADMIN_SYNC,
}


def map_easyone_permissions(easyone_permissions: list[str]) -> list[str]:
    """Converte permessi EasyOne in scope MAC AI."""
    scopes: set[str] = set()
    for perm in easyone_permissions:
        normalized = perm.strip().lower()
        if normalized in EASYONE_PERMISSION_MAP:
            scopes.add(EASYONE_PERMISSION_MAP[normalized])
        elif normalized in ALL_SCOPES:
            scopes.add(normalized)
    return sorted(scopes)


def has_scope(user_permissions: list[str], required: str | Scope) -> bool:
    required_value = required.value if isinstance(required, Scope) else required
    if required_value in user_permissions:
        return True
    return Scope.ADMIN_SYNC.value in user_permissions and required_value.startswith(
        ("admin:",)
    )
