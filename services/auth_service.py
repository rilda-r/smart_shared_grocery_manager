"""
services/auth_service.py

Registration, authentication with failed-login lockout, and session-token
support.

Conventions shared by ALL services
----------------------------------
* Every service returns ``{"success", "data", "message", "error_code"}``.
* Functions other than ``register_user`` / ``authenticate_user`` take the
  authenticated ``user_id`` as their FIRST argument. The UI must take it from
  the ``authenticate_user`` / ``validate_session`` result, never from user input.
"""

from datetime import datetime, timedelta

from config.settings import LOCKOUT_MINUTES, MAX_FAILED_LOGIN_ATTEMPTS
from database.connection import DatabaseError, execute, get_cursor, query_one
from models.user import User
from utils.helpers import ServiceError, service_call, success_response, utcnow
from utils.security import (
    burn_password_check,
    clear_unknown_identifier,
    create_session_token,
    hash_password,
    record_unknown_identifier_failure,
    revoke_session_token,
    unknown_identifier_locked,
    verify_password,
    verify_session_token,
)
from utils.validators import (
    validate_email,
    validate_id,
    validate_password,
    validate_username,
)

GENERIC_LOGIN_ERROR = "Invalid email/username or password."
LOCKED_MESSAGE = (
    f"Too many failed attempts. Please try again in {LOCKOUT_MINUTES} minutes."
)


def require_user(user_id, cursor=None) -> dict:
    """Return the user row for an authenticated ``user_id`` or raise."""
    validate_id(user_id, "user id")
    row = query_one("SELECT * FROM users WHERE id = %s", (user_id,), cursor)
    if row is None:
        raise ServiceError("Authentication required.", "unauthorized")
    return row


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _find_user(identifier: str, cursor, for_update: bool = False):
    column = "email" if "@" in identifier else "username"
    value = identifier.lower() if column == "email" else identifier
    sql = f"SELECT * FROM users WHERE {column} = %s" + (" FOR UPDATE" if for_update else "")
    return query_one(sql, (value,), cursor)


@service_call
def register_user(username, email, password):
    username = validate_username(username)
    email = validate_email(email)
    validate_password(password)
    password_hash = hash_password(password)
    try:
        user_id = execute(
            "INSERT INTO users (username, email, password_hash, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (username, email, password_hash, utcnow()),
        )
    except DatabaseError as exc:
        if exc.is_duplicate:
            raise ServiceError(
                "That username or email is already registered.", "duplicate_user"
            )
        raise
    row = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
    return success_response(User.from_row(row).to_dict(), "Account created.")


@service_call
def authenticate_user(identifier, password):
    """Log in with email OR username. Returns the user and a session token."""
    identifier = identifier.strip() if isinstance(identifier, str) else ""
    if not identifier or not isinstance(password, str) or not password:
        raise ServiceError(GENERIC_LOGIN_ERROR, "invalid_credentials")
    key = identifier.lower()
    outcome, user_row = "invalid", None

    with get_cursor() as cur:
        row = _find_user(identifier, cur, for_update=True)
        if row is None:
            if unknown_identifier_locked(key):
                burn_password_check(password)
                outcome = "locked"
            else:
                burn_password_check(password)
                record_unknown_identifier_failure(key)
        else:
            now = utcnow()
            locked_until = _parse_ts(row["locked_until"])
            attempts = row["failed_login_attempts"] or 0
            if locked_until and locked_until > now:
                burn_password_check(password)
                outcome = "locked"
            else:
                if locked_until:  # lock expired
                    attempts = 0
                if verify_password(password, row["password_hash"]):
                    execute(
                        "UPDATE users SET failed_login_attempts = 0, locked_until = NULL "
                        "WHERE id = %s",
                        (row["id"],),
                        cur,
                    )
                    outcome, user_row = "ok", row
                else:
                    attempts += 1
                    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                        until = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                        execute(
                            "UPDATE users SET failed_login_attempts = 0, locked_until = %s "
                            "WHERE id = %s",
                            (until, row["id"]),
                            cur,
                        )
                    else:
                        execute(
                            "UPDATE users SET failed_login_attempts = %s, locked_until = NULL "
                            "WHERE id = %s",
                            (attempts, row["id"]),
                            cur,
                        )

    if outcome == "locked":
        raise ServiceError(LOCKED_MESSAGE, "account_locked")
    if outcome != "ok":
        raise ServiceError(GENERIC_LOGIN_ERROR, "invalid_credentials")
    clear_unknown_identifier(key)
    return success_response(
        {
            "user": User.from_row(user_row).to_dict(),
            "session_token": create_session_token(user_row["id"]),
        },
        "Login successful.",
    )


@service_call
def validate_login_attempts(identifier):
    """Report lock state without revealing whether the account exists."""
    identifier = identifier.strip() if isinstance(identifier, str) else ""
    locked = False
    if identifier:
        with get_cursor() as cur:
            row = _find_user(identifier, cur)
        if row is None:
            locked = unknown_identifier_locked(identifier.lower())
        else:
            until = _parse_ts(row["locked_until"])
            locked = bool(until and until > utcnow())
    return success_response(
        {"locked": locked, "lockout_minutes": LOCKOUT_MINUTES if locked else 0}
    )


@service_call
def validate_session(session_token):
    """Resolve a session token to the (public) user, or fail as unauthorized."""
    user_id = verify_session_token(session_token)
    if user_id is None:
        raise ServiceError("Your session has expired. Please log in again.", "unauthorized")
    return success_response(User.from_row(require_user(user_id)).to_dict())


@service_call
def logout_user(session_token):
    """Revoke the session token (server-side logout)."""
    revoke_session_token(session_token)
    return success_response(None, "Logged out.")
