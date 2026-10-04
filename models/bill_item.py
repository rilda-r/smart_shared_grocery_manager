"""models/bill_item.py - BillItem model (maps to ``bill_items``)."""

from dataclasses import asdict, dataclass, fields
from decimal import Decimal
from typing import Optional


@dataclass
class BillItem:
    id: int
    bill_id: int
    item_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    matched_grocery_item_id: Optional[int]
    assigned_user_id: Optional[int]

    @classmethod
    def from_row(cls, row: dict) -> "BillItem":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
