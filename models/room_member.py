"""models/room_member.py - RoomMember model (maps to ``room_members``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Optional


@dataclass
class RoomMember:
    room_id: int
    user_id: int
    role: str
    joined_at: Optional[datetime]

    @classmethod
    def from_row(cls, row: dict) -> "RoomMember":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self) -> dict:
        return asdict(self)
