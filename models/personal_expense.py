"""models/personal_expense.py - PersonalExpense model (maps to ``personal_expenses``)."""

from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PersonalExpense:
    id: int
    user_id: int
    amount: Decimal
    category: str
    expense_date: date
    description: Optional[str]
    created_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "PersonalExpense":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
