"""
security/authentication.py
==========================
Security and credential validation utilities for GrocEase.
Integrates with services.email_service for live SMTP delivery and event triggers.
"""

import os
import re
import unicodedata
from datetime import datetime, timedelta

from services.email_service import (
    smtp_is_configured,
    send_otp_email,
    send_welcome_email,
    send_account_deleted_email,
)

# Cooldown and Expiry settings
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_EXPIRY_MINUTES = 10


def clean_email_input(raw: str) -> str:
    """Remove invisible characters, brackets/quotes and whitespace; lowercase."""
    s = unicodedata.normalize("NFKC", raw or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) not in ("Cf", "Cc"))
    return s.strip().strip("<>\"' ,;").lower()


def is_valid_email(email: str) -> bool:
    """
    Strictly validates email string using RFC-compliant validation and regex fallbacks.
    """
    if not email or not isinstance(email, str):
        return False
    clean = email.strip()
    if len(clean) > 255:
        return False
    try:
        from email_validator import validate_email as _ev, EmailNotValidError
        _ev(clean, check_deliverability=False)
        return True
    except Exception:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, clean))


def generate_otp() -> str:
    """Generates a secure 6-digit numerical string OTP."""
    import secrets
    return f"{secrets.randbelow(900000) + 100000}"


def otp_expiry_time() -> datetime:
    """Returns the precise timestamp for when the OTP will expire."""
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)


def is_otp_expired(expiry_time: datetime) -> bool:
    """Checks if the current time has surpassed the token expiration time."""
    return datetime.utcnow() > expiry_time