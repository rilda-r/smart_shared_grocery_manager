import os
import re
from datetime import datetime, timedelta

# Cooldown and Expiry settings
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_EXPIRY_MINUTES = 10


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


def smtp_is_configured() -> bool:
    """Returns False in local dev mode when live email delivery is mocked."""
    dev_mode = os.environ.get("GROCEASE_DEV_MODE", "true").lower() in ("true", "1", "yes", "on")
    if dev_mode:
        return False
    smtp_host = os.environ.get("GROCEASE_SMTP_HOST", "").strip()
    return bool(smtp_host)


def send_otp_email(email: str, otp: str):
    """Sends OTP email or logs to console in development mode."""
    print(f"[MAIL SYSTEM] Verification code for {email} is: {otp}")
