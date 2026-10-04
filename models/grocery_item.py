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

    @classmethod
    def from_row(cls, row: dict) -> "GroceryItem":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
