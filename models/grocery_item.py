"""models/grocery_item.py - GroceryItem model (maps to ``grocery_items``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Optional


@dataclass
class GroceryItem:
    id: int
    room_id: int
    user_id: int
    item_name: str
    quantity: int
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    purchased_quantity: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "GroceryItem":
        data = {}
        for f in fields(cls):
            val = row.get(f.name)
            if val is None and f.name == "purchased_quantity":
                val = 0
            data[f.name] = val
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)
