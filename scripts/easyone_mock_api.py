#!/usr/bin/env python3
"""
Mock API EasyOne/ERP per sviluppo e test integrazione.

Avvio:
  python scripts/easyone_mock_api.py

Configurazione hub (.env):
  EASYONE_MODE=hybrid
  EASYONE_AUTH_MODE=http
  EASYONE_BASE_URL=http://127.0.0.1:8090
  ERP_BASE_URL=http://127.0.0.1:8090
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="EasyOne Mock API", version="1.0")

MOCK_USERS = {"admin": "admin", "commerciale": "commerciale"}
MOCK_CUSTOMERS = [
    {
        "customer_code": "EO-1001",
        "company_name": "Alpha Tech Srl",
        "phone": "+393201112233",
        "email": "ordini@alphatech.it",
        "city": "Milano",
        "sales_agent": "Marco Rossi",
    },
    {
        "customer_code": "EO-1002",
        "company_name": "Beta Informatica SpA",
        "phone": "+393204445566",
        "email": "acquisti@betainfo.it",
        "city": "Roma",
        "sales_agent": "Laura Bianchi",
    },
]
MOCK_PRODUCTS = [
    {
        "internal_code": "RT-AX58U",
        "manufacturer": "ASUS",
        "description": "Router WiFi 6 AX3000",
        "category": "Networking",
        "availability": 24,
        "price": "129.90",
    },
    {
        "internal_code": "TL-SG108",
        "manufacturer": "TP-Link",
        "description": "Switch Gigabit 8 porte",
        "category": "Networking",
        "availability": 3,
        "price": "24.50",
    },
]
MOCK_ORDERS = [
    {
        "order_number": "EO-ORD-9001",
        "order_date": "2025-11-12",
        "customer_code": "EO-1001",
        "lines": [
            {"product_code": "RT-AX58U", "quantity": "2", "unit_price": "125.00"},
            {"product_code": "TL-SG108", "quantity": "4", "unit_price": "22.00"},
        ],
    }
]


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict:
    if MOCK_USERS.get(payload.username) != payload.password:
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    return {
        "user_id": f"eo-{payload.username}",
        "username": payload.username,
        "display_name": payload.username.title(),
        "roles": ["commerciale"],
        "permissions": ["catalogo.lettura", "magazzino.lettura", "clienti.lettura", "ai.chat"],
        "access_token": f"mock-token-{payload.username}",
    }


@app.get("/api/customers/search")
def search_customers(q: str, limit: int = 20) -> dict:
    q_lower = q.lower()
    items = [
        c
        for c in MOCK_CUSTOMERS
        if q_lower in c["company_name"].lower() or q_lower in c["customer_code"].lower()
    ]
    return {"items": items[:limit], "total": len(items)}


@app.get("/api/customers/{code}")
def get_customer(code: str) -> dict:
    for c in MOCK_CUSTOMERS:
        if c["customer_code"] == code:
            return c
    raise HTTPException(status_code=404)


@app.get("/api/products/search")
def search_products(q: str, limit: int = 20) -> dict:
    q_lower = q.lower()
    items = [
        p
        for p in MOCK_PRODUCTS
        if q_lower in p["internal_code"].lower() or q_lower in p["description"].lower()
    ]
    return {"items": items[:limit]}


@app.get("/api/products/{code}")
def get_product(code: str) -> dict:
    for p in MOCK_PRODUCTS:
        if p["internal_code"] == code:
            return p
    raise HTTPException(status_code=404)


@app.get("/api/warehouse/search")
def search_stock(q: str, limit: int = 20) -> dict:
    items = []
    for p in MOCK_PRODUCTS:
        if q.lower() in p["internal_code"].lower():
            items.append(
                {
                    "internal_code": p["internal_code"],
                    "product": p,
                    "availability": p["availability"],
                    "warehouse_code": "MAG-01",
                    "location": "A-12-03",
                }
            )
    return {"items": items[:limit]}


@app.get("/api/warehouse/stock/{code}")
def get_stock(code: str) -> dict:
    for p in MOCK_PRODUCTS:
        if p["internal_code"] == code:
            return {
                "internal_code": code,
                "product": p,
                "availability": p["availability"],
                "warehouse_code": "MAG-01",
                "location": "A-12-03",
            }
    raise HTTPException(status_code=404)


@app.get("/api/orders/search")
def search_orders(limit: int = 50) -> dict:
    return {"items": MOCK_ORDERS[:limit]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8090)
