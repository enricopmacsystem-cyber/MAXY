#!/usr/bin/env python3
"""Test integrazione MVP2 — Mock EasyOne + client HTTP hub."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import httpx

MOCK_URL = "http://127.0.0.1:8090"
HUB_URL = "http://127.0.0.1:8000"

passed = 0
failed = 0
skipped = 0


def ok(name: str, detail: str = "") -> None:
    global passed
    passed += 1
    print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))


def fail(name: str, detail: str) -> None:
    global failed
    failed += 1
    print(f"  FAIL  {name} — {detail}")


def skip(name: str, reason: str) -> None:
    global skipped
    skipped += 1
    print(f"  SKIP  {name} — {reason}")


def test_mock_api() -> str | None:
    print("\n=== Mock EasyOne API (porta 8090) ===")
    token = None
    try:
        with httpx.Client(timeout=10.0) as client:
            # Health implicito
            r = client.get(f"{MOCK_URL}/api/customers/search", params={"q": "Alpha"})
            if r.status_code != 200:
                fail("customers/search", f"status {r.status_code}")
            else:
                data = r.json()
                n = len(data.get("items", []))
                ok("customers/search", f"{n} clienti trovati")

            r = client.post(
                f"{MOCK_URL}/api/auth/login",
                json={"username": "admin", "password": "admin"},
            )
            if r.status_code != 200:
                fail("auth/login", f"status {r.status_code}")
            else:
                data = r.json()
                token = data.get("access_token")
                ok("auth/login", f"user={data.get('username')} token={'sì' if token else 'no'}")

            r = client.get(f"{MOCK_URL}/api/products/search", params={"q": "router"})
            if r.status_code == 200 and r.json().get("items"):
                ok("products/search", r.json()["items"][0].get("internal_code", ""))
            else:
                fail("products/search", str(r.status_code))

            r = client.get(f"{MOCK_URL}/api/warehouse/stock/RT-AX58U")
            if r.status_code == 200:
                stock = r.json().get("availability", "?")
                ok("warehouse/stock", f"RT-AX58U giacenza={stock}")
            else:
                fail("warehouse/stock", str(r.status_code))

            r = client.get(f"{MOCK_URL}/api/orders/search")
            if r.status_code == 200 and r.json().get("items"):
                ok("orders/search", r.json()["items"][0].get("order_number", ""))
            else:
                fail("orders/search", str(r.status_code))

    except httpx.ConnectError:
        fail("mock_api", "Mock non raggiungibile su :8090 — avviare easyone_mock_api.py")
    return token


def test_hub_clients(token: str | None) -> None:
    print("\n=== Client HTTP Integration Hub ===")
    import os

    os.environ["EASYONE_BASE_URL"] = MOCK_URL
    os.environ["ERP_BASE_URL"] = MOCK_URL
    os.environ["EASYONE_MODE"] = "hybrid"
    os.environ["EASYONE_AUTH_MODE"] = "http"

    from app.config.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    from app.integrations.easyone.auth_client import HttpEasyOneAuthClient
    from app.integrations.easyone.customers_client import EasyOneCustomersClient
    from app.integrations.easyone.http_client import EasyOneHttpClient, get_erp_client
    from app.integrations.easyone.orders_client import EasyOneOrdersClient
    from app.integrations.easyone.products_client import EasyOneProductsClient
    from app.integrations.easyone.stock_client import EasyOneStockClient

    try:
        profile = HttpEasyOneAuthClient(settings).authenticate("admin", "admin")
        ok("HttpEasyOneAuthClient", profile.display_name)
        token = profile.easyone_access_token or token
    except Exception as exc:
        fail("HttpEasyOneAuthClient", str(exc))

    http = EasyOneHttpClient(settings, access_token=token)
    customers = EasyOneCustomersClient(http).search("Beta", limit=5)
    if customers:
        ok("EasyOneCustomersClient", customers[0].company_name)
    else:
        fail("EasyOneCustomersClient", "nessun risultato")

    product = EasyOneProductsClient(http).get_product_by_code("RT-AX58U")
    if product:
        ok("EasyOneProductsClient", f"{product.internal_code} €{product.price}")
    else:
        fail("EasyOneProductsClient", "prodotto non trovato")

    erp = get_erp_client(settings, access_token=token)
    stock = EasyOneStockClient(erp).get_stock("TL-SG108")
    if stock:
        ok("EasyOneStockClient", f"TL-SG108 qty={stock.availability.quantity}")
    else:
        fail("EasyOneStockClient", "giacenza non trovata")

    orders = EasyOneOrdersClient(http).search(limit=10)
    if orders:
        parsed = EasyOneOrdersClient().parse_order(orders[0])
        ok("EasyOneOrdersClient", parsed["order_number"] if parsed else "?")
    else:
        fail("EasyOneOrdersClient", "nessun ordine")


def test_hub_api() -> None:
    print("\n=== Integration Hub FastAPI (porta 8000) ===")
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{HUB_URL}/api/health")
            if r.status_code != 200:
                skip("hub/health", f"status {r.status_code}")
                return
            health = r.json()
            ok("hub/health", f"db={health.get('database')} v={health.get('version')}")

            if health.get("database") != "up":
                skip("hub/auth/login", "PostgreSQL non disponibile")
                skip("hub/customers", "PostgreSQL non disponibile")
                skip("hub/warehouse", "PostgreSQL non disponibile")
                skip("hub/sync", "PostgreSQL non disponibile")
                return

            r = client.post(
                f"{HUB_URL}/api/auth/login",
                json={"username": "admin", "password": "admin"},
            )
            if r.status_code != 200:
                fail("hub/auth/login", r.text[:200])
                return
            tokens = r.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            ok("hub/auth/login", tokens["user"]["username"])

            r = client.get(f"{HUB_URL}/api/customers/search", params={"q": "Alpha"}, headers=headers)
            if r.status_code == 200 and r.json().get("items"):
                ok("hub/customers/search", r.json()["items"][0]["company_name"])
            else:
                fail("hub/customers/search", r.text[:200])

            r = client.get(f"{HUB_URL}/api/warehouse/search", params={"q": "RT"}, headers=headers)
            if r.status_code == 200 and r.json().get("items"):
                item = r.json()["items"][0]
                ok("hub/warehouse/search", f"{item['product']['internal_code']} src={item.get('source')}")
            else:
                fail("hub/warehouse/search", r.text[:200])

            r = client.post(f"{HUB_URL}/api/sync/orders", headers=headers)
            if r.status_code == 200:
                data = r.json()
                ok("hub/sync/orders", f"ordini={data.get('orders_imported', 0)}")
            else:
                fail("hub/sync/orders", r.text[:200])

    except httpx.ConnectError:
        skip("hub", "Hub non raggiungibile su :8000 — avviare run_hub.py")


def main() -> int:
    print("MAC AI Assistant — Test integrazione MVP2")
    token = test_mock_api()
    if token is not None or passed > 0:
        test_hub_clients(token)
    test_hub_api()

    print(f"\n=== Risultato: {passed} PASS, {failed} FAIL, {skipped} SKIP ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
