"""models/budget.py - Budget model (maps to ``budgets``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Budget:
    id: int
    user_id: int
    category: str
    monthly_limit: Decimal
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "Budget":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
