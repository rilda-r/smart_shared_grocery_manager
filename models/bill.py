"""models/bill.py - Bill model (maps to ``bills``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Bill:
    id: int
    room_id: int
    uploaded_by: int
    file_name: str
    ocr_status: str
    total_amount: Decimal
    created_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "Bill":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
