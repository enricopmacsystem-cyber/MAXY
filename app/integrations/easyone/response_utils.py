from __future__ import annotations

from typing import Any


def macsystem_list_params(
    *,
    take: int,
    skip: int = 0,
    search_value: str = "",
) -> dict[str, Any]:
    """Parametri query standard API EasyOne Mac System (people, articles, joborders)."""
    params: dict[str, Any] = {"take": take, "skip": skip}
    if search_value.strip():
        params["searchValue"] = search_value.strip()
    return params


def extract_easyone_items(data: Any) -> list[dict[str, Any]]:
    """Estrae una lista di record da risposte EasyOne (array o wrapper JSON)."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    for key in ("items", "data", "results", "value", "records", "rows"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    total = data.get("totalCount") or data.get("total")
    if total and isinstance(data.get("list"), list):
        return [item for item in data["list"] if isinstance(item, dict)]

    return []
