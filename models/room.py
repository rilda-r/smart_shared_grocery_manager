"""models/room.py - Room model (maps to ``rooms``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Optional


@dataclass
class Room:
    id: int
    name: str
    secret_code: str
    creator_id: int
    created_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "Room":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
