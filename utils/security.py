"""
utils/security.py

Password hashing (bcrypt), signed session tokens, login throttling for
unknown identifiers, and secure random room codes.
"""

import base64
import hashlib
import hmac
import secrets
import threading
import time

import bcrypt

from config.settings import (
    LOCKOUT_MINUTES,
    MAX_FAILED_LOGIN_ATTEMPTS,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    get_settings,
)


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), (password_hash or "").encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


_dummy_hash = None


def burn_password_check(plain_password: str) -> None:
    """Spend the same time as a real verification (unknown-account timing)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(12))
    verify_password(plain_password, _dummy_hash)


# ---------------------------------------------------------------------------
# Session tokens (stateless HMAC + in-process revocation list)
# ---------------------------------------------------------------------------
_revoked = {}
_revoked_lock = threading.Lock()


def _sign(payload: str) -> str:
    key = get_settings().secret_key.encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    expires = int(time.time()) + get_settings().session_ttl_seconds
    payload = f"{int(user_id)}:{expires}:{secrets.token_hex(8)}"
    raw = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def verify_session_token(token):
    """Return ``user_id`` for a valid, unexpired, unrevoked token, else None."""
    try:
        raw = base64.urlsafe_b64decode(str(token).encode("ascii")).decode("utf-8")
        user_id, expires, nonce, signature = raw.split(":")
        payload = f"{user_id}:{expires}:{nonce}"
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        if int(expires) < time.time():
            return None
        with _revoked_lock:
            if token in _revoked:
                return None
        return int(user_id)
    except Exception:  # malformed token of any kind
        return None


def revoke_session_token(token) -> None:
    now = time.time()
    with _revoked_lock:
        for key in [k for k, exp in _revoked.items() if exp < now]:
            del _revoked[key]
        _revoked[token] = now + get_settings().session_ttl_seconds


# ---------------------------------------------------------------------------
# Throttle for identifiers that do not match an account (keeps responses
# indistinguishable from real accounts: no account-existence leak).
# ---------------------------------------------------------------------------
_unknown_attempts = {}
_unknown_lock = threading.Lock()


def unknown_identifier_locked(identifier: str) -> bool:
    with _unknown_lock:
        entry = _unknown_attempts.get(identifier)
        if not entry:
            return False
        count, locked_until = entry
        if locked_until and locked_until > time.time():
            return True
        if locked_until:
            del _unknown_attempts[identifier]
        return False


def record_unknown_identifier_failure(identifier: str) -> None:
    with _unknown_lock:
        count, locked_until = _unknown_attempts.get(identifier, (0, 0))
        count += 1
        if count >= MAX_FAILED_LOGIN_ATTEMPTS:
            _unknown_attempts[identifier] = (0, time.time() + LOCKOUT_MINUTES * 60)
        else:
            _unknown_attempts[identifier] = (count, 0)


def clear_unknown_identifier(identifier: str) -> None:
    with _unknown_lock:
        _unknown_attempts.pop(identifier, None)


# ---------------------------------------------------------------------------
# Room codes
# ---------------------------------------------------------------------------
def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
