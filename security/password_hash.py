"""
security/password_hash.py

Handles secure password hashing and verification using bcrypt
(salted, adaptive hashing — never store or compare raw passwords).
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt with a fresh random salt.
    Returns the hash as a UTF-8 string, safe to store in the database.
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.
    Returns True if it matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def password_strength(password: str) -> dict:
    """
    Evaluate password strength against GrocEase's requirements.
    Returns a dict of individual checks plus an overall 'valid' flag.
    """
    checks = {
        "length": len(password) >= 8,
        "uppercase": any(c.isupper() for c in password),
        "lowercase": any(c.islower() for c in password),
        "number": any(c.isdigit() for c in password),
        "special": any(not c.isalnum() for c in password if not c.isspace())
        and any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password),
    }
    checks["valid"] = all(checks.values())
    return checks
