"""
utils/helpers.py

Backend helpers shared by every service:

* the uniform response envelope returned by all service functions
* ``ServiceError`` + ``service_call`` (controlled error handling)
* money / time helpers (Decimal only, never float)
"""

import functools
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from database.connection import DatabaseError

logger = logging.getLogger("grocease")

MONEY_QUANT = Decimal("0.01")
UNSET = object()  # sentinel: "argument not supplied" (distinct from None)


# ---------------------------------------------------------------------------
# Response envelope
# ---------------------------------------------------------------------------
def success_response(data=None, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message, "error_code": None}


def error_response(message: str, error_code: str = "error", data=None) -> dict:
    return {
        "success": False,
        "data": data,
        "message": message,
        "error_code": error_code,
    }


class ServiceError(Exception):
    """Controlled, user-presentable error raised inside services."""

    def __init__(self, message: str, error_code: str = "error", data=None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.data = data


class ValidationError(ServiceError):
    def __init__(self, message: str, data=None):
        super().__init__(message, "invalid_input", data)


def service_call(func):
    """Convert exceptions into the standard error envelope.

    Raw SQL / driver exceptions are logged server-side and never exposed.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ServiceError as exc:
            return error_response(exc.message, exc.error_code, exc.data)
        except DatabaseError:
            logger.exception("Database failure in %s", func.__name__)
            return error_response(
                "A database error occurred. Please try again later.",
                "database_error",
            )
        except Exception:  # noqa: BLE001 - last-resort safety net
            logger.exception("Unexpected failure in %s", func.__name__)
            return error_response(
                "An unexpected error occurred. Please try again.",
                "internal_error",
            )

    return wrapper


# ---------------------------------------------------------------------------
# Money / time
# ---------------------------------------------------------------------------
def to_money(value) -> Decimal:
    """Convert to a 2dp Decimal (ROUND_HALF_UP). Floats are routed via str()."""
    if isinstance(value, bool):
        raise ValidationError("Invalid amount.")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValidationError("Invalid amount.")
    if not number.is_finite():
        raise ValidationError("Invalid amount.")
    return number.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def utcnow() -> datetime:
    """Naive UTC timestamp (matches MySQL DATETIME columns)."""
    return datetime.utcnow().replace(microsecond=0)


def month_bounds(year: int, month: int):
    """Return (first_day, first_day_of_next_month) as dates."""
    from datetime import date

    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end
