"""models/payment.py - Payment model (maps to ``payments``).

``payer_user_id`` owes ``amount`` to ``payee_user_id`` (the member who paid the bill).
"""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Payment:
    id: int
    room_id: int
    bill_id: int
    payer_user_id: int
    payee_user_id: int
    amount: Decimal
    payment_status: str
    created_at: Optional[datetime]
    settled_at: Optional[datetime]
    reported_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "Payment":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
