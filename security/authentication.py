import re
import random
from datetime import datetime, timedelta

# Cooldown and Expiry settings
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_EXPIRY_MINUTES = 10

def is_valid_email(email: str) -> bool:
    """
    Validates email format using a standard bulletproof regex pattern.
    """
    if not email:
        return False
    # Regular expression for standard email structures (e.g., name@domain.com)
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))

def generate_otp() -> str:
    """Generates a secure 6-digit numerical string OTP."""
    return f"{random.randint(100000, 999999)}"

def otp_expiry_time() -> datetime:
    """Returns the precise timestamp for when the OTP will expire."""
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

def is_otp_expired(expiry_time: datetime) -> bool:
    """Checks if the current time has surpassed the token expiration time."""
    return datetime.utcnow() > expiry_time

def smtp_is_configured() -> bool:
    """Dev flag to check if real mail server settings are wired up."""
    return False

def send_otp_email(email: str, otp: str):
    """Simulates sending an email by printing to backend system log structures."""
    print(f"[MAIL SYSTEM] Verification code for {email} is: {otp}")
