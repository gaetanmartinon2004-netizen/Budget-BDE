from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Mandat:
    id: int | None
    name: str
    date_debut: str
    date_fin: str
    active: bool = True


@dataclass
class BudgetNode:
    id: int | None
    mandat_id: int
    parent_id: int | None
    name: str
    pole_color: str | None = None
    children: list[BudgetNode] | None = None


@dataclass
class Transaction:
    id: int | None
    mandat_id: int
    node_id: int
    flow_type: str
    amount: float
    label: str | None = None
    description: str | None = None
    date: str = ""
    payment_method: str | None = None
    order_number: str | None = None


@dataclass
class BudgetPlan:
    id: int | None
    mandat_id: int
    node_id: int
    year: int
    flow_type: str
    amount: float


def dict_from_row(row: Any) -> dict[str, Any]:
    """Convert sqlite3.Row to dict"""
    if row is None:
        return {}
    return dict(row)
