"""models/user.py - User model (maps to ``users``)."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    username: Optional[str]
    email: str
    password_hash: str
    created_at: Optional[datetime]
    full_name: Optional[str] = None
    nickname: Optional[str] = None


    @classmethod
    def from_row(cls, row: dict) -> "User":
        return cls(**{f.name: row.get(f.name) for f in fields(cls)})

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Public representation. The password hash is NEVER included by default."""
        data = asdict(self)
        if not include_sensitive:
            data.pop("password_hash", None)
        return data

    def __repr__(self) -> str:  # never leak the hash into logs
        return f"User(id={self.id!r}, username={self.username!r}, email={self.email!r})"
