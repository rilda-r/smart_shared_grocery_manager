"""
config/settings.py

Central, environment-driven configuration for the GrocEase backend.

Nothing secret is hard-coded: database credentials, the session signing key
and OCR credentials are all read from environment variables (optionally via a
local ``.env`` file). Settings are read lazily so tests can override the
environment before the first database call.
"""

import os
import secrets
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Business constants (not secrets, safe to keep in code)
# ---------------------------------------------------------------------------
MAX_FAILED_LOGIN_ATTEMPTS = 3
LOCKOUT_MINUTES = 30

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt input limit

ROOM_CODE_LENGTH = 8
ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I

GROCERY_STATUSES = ("pending", "purchased", "unavailable")
OCR_STATUSES = ("pending", "processing", "completed", "failed")
PAYMENT_STATUSES = ("pending", "settled", "reported")
ROOM_ROLES = ("creator", "member")

MAX_MONEY = 99999999  # DECIMAL(10,2) ceiling (exclusive of cents)

ALLOWED_BILL_EXTENSIONS = ("png", "jpg", "jpeg", "pdf")

# Process-local fallback key; never persisted, never hard-coded.
_EPHEMERAL_SECRET_KEY = secrets.token_urlsafe(48)


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_user: str
    db_password: str = field(repr=False)
    db_name: str
    secret_key: str = field(repr=False)
    session_ttl_seconds: int
    bcrypt_rounds: int
    max_upload_bytes: int
    ocr_provider: str
    tesseract_cmd: str
    ocr_language: str
    db_url: str = ""
    db_sslmode: str = "prefer"
    dev_mode: bool = True


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def get_settings() -> Settings:
    """Build a fresh Settings snapshot from the current environment."""
    db_url = (
        os.environ.get("GROCEASE_DB_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    dev_mode_str = os.environ.get("GROCEASE_DEV_MODE", "true").lower()
    dev_mode = dev_mode_str in ("true", "1", "yes", "on")

    return Settings(
        db_host=os.environ.get("GROCEASE_DB_HOST") or os.environ.get("SUPABASE_DB_HOST", "localhost"),
        db_port=_int_env("GROCEASE_DB_PORT", _int_env("SUPABASE_DB_PORT", 5432)),
        db_user=os.environ.get("GROCEASE_DB_USER") or os.environ.get("SUPABASE_DB_USER", "postgres"),
        db_password=os.environ.get("GROCEASE_DB_PASSWORD") or os.environ.get("SUPABASE_DB_PASSWORD", ""),
        db_name=os.environ.get("GROCEASE_DB_NAME") or os.environ.get("SUPABASE_DB_NAME", "postgres"),
        secret_key=os.environ.get("GROCEASE_SECRET_KEY") or _EPHEMERAL_SECRET_KEY,
        session_ttl_seconds=_int_env("GROCEASE_SESSION_TTL_SECONDS", 8 * 3600),
        bcrypt_rounds=max(4, min(_int_env("GROCEASE_BCRYPT_ROUNDS", 12), 15)),
        max_upload_bytes=_int_env("GROCEASE_MAX_UPLOAD_MB", 10) * 1024 * 1024,
        ocr_provider=os.environ.get("GROCEASE_OCR_PROVIDER", "tesseract").lower(),
        tesseract_cmd=os.environ.get("GROCEASE_TESSERACT_CMD", ""),
        ocr_language=os.environ.get("GROCEASE_OCR_LANGUAGE", "eng"),
        db_url=db_url,
        db_sslmode=os.environ.get("GROCEASE_DB_SSLMODE", "prefer"),
        dev_mode=dev_mode,
    )

