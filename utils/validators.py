"""
utils/validators.py

Input validation. Every validator either returns a normalised value or raises
``ValidationError`` (a ``ServiceError``) with a user-presentable message.
"""

import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from config.settings import (
    ALLOWED_BILL_EXTENSIONS,
    GROCERY_STATUSES,
    MAX_MONEY,
    MAX_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    get_settings,
)
from utils.helpers import ValidationError, to_money

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
_SPECIALS = set("!@#$%^&*()_+-=[]{}|;:,.<>?/~`'\"\\")

_MAGIC = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "pdf": (b"%PDF-",),
}


def validate_id(value, name: str = "id") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"Invalid {name}.")
    return value


def validate_username(username) -> str:
    username = (username or "").strip() if isinstance(username, str) else ""
    if not _USERNAME_RE.match(username):
        raise ValidationError(
            "Username must be 3-30 characters: letters, numbers, '.', '_' or '-'."
        )
    return username


def validate_email(email) -> str:
    email = email.strip().lower() if isinstance(email, str) else ""
    if not email or len(email) > 255:
        raise ValidationError("Please enter a valid email address.")
    try:
        from email_validator import EmailNotValidError, validate_email as _ev

        try:
            return _ev(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            raise ValidationError("Please enter a valid email address.")
    except ImportError:  # library optional; regex fallback
        if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
            raise ValidationError("Please enter a valid email address.")
        return email


def password_problems(password) -> list:
    """List the unmet password rules (empty list == valid)."""
    if not isinstance(password, str):
        return ["Password is required."]
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        problems.append(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
    if not any(c.isupper() for c in password):
        problems.append("Password must contain an uppercase letter.")
    if not any(c.isdigit() for c in password):
        problems.append("Password must contain a number.")
    if not any(c in _SPECIALS for c in password):
        problems.append("Password must contain a special character.")
    return problems


def validate_password(password) -> str:
    problems = password_problems(password)
    if problems:
        raise ValidationError(" ".join(problems), data={"problems": problems})
    return password


def _clean_text(value, label: str, max_len: int, required: bool = True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{label} is required.")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{label} is invalid.")
    value = " ".join(value.split())  # collapse whitespace/control chars
    if any(ord(c) < 32 for c in value):
        raise ValidationError(f"{label} contains invalid characters.")
    if len(value) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters.")
    return value


def validate_room_name(name) -> str:
    return _clean_text(name, "Room name", 100)


def validate_item_name(name) -> str:
    return _clean_text(name, "Item name", 255)


def validate_category(category) -> str:
    return _clean_text(category, "Category", 50)


def validate_description(description):
    return _clean_text(description, "Description", 255, required=False)


def normalize_room_code(code) -> str:
    return code.strip().upper() if isinstance(code, str) else ""


def is_valid_room_code_format(code: str) -> bool:
    return len(code) == ROOM_CODE_LENGTH and all(c in ROOM_CODE_ALPHABET for c in code)


def validate_grocery_status(status) -> str:
    if status not in GROCERY_STATUSES:
        raise ValidationError(
            "Status must be one of: " + ", ".join(GROCERY_STATUSES) + "."
        )
    return status


def validate_grocery_quantity(quantity) -> int:
    if isinstance(quantity, bool):
        raise ValidationError("Quantity must be a whole number greater than zero.")
    try:
        number = Decimal(str(quantity))
    except Exception:
        raise ValidationError("Quantity must be a whole number greater than zero.")
    if number != number.to_integral_value() or number < 1 or number > 10000:
        raise ValidationError("Quantity must be a whole number between 1 and 10000.")
    return int(number)


def validate_amount(value, label: str = "Amount", allow_zero: bool = False) -> Decimal:
    amount = to_money(value)
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValidationError(f"{label} must be greater than zero.")
    if amount > MAX_MONEY:
        raise ValidationError(f"{label} is too large.")
    return amount


def validate_bill_quantity(value) -> Decimal:
    try:
        number = Decimal(str(value))
    except Exception:
        raise ValidationError("Invalid bill item quantity.")
    if not number.is_finite() or number <= 0 or number > 100000:
        raise ValidationError("Invalid bill item quantity.")
    return number.quantize(Decimal("0.001"))


def validate_expense_date(value) -> date:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value.strip())
        except ValueError:
            raise ValidationError("Expense date must be in YYYY-MM-DD format.")
    if not isinstance(value, date):
        raise ValidationError("Expense date is required.")
    if value.year < 2000 or value > date.today() + timedelta(days=366):
        raise ValidationError("Expense date is out of range.")
    return value


def sanitize_file_name(file_name) -> str:
    base = os.path.basename(str(file_name or "").replace("\\", "/"))
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base[:255]


def validate_bill_file(file_name, file_bytes) -> str:
    """Validate an uploaded bill by extension, size and magic bytes.

    Returns the sanitised file name (also the lowercase extension check basis).
    """
    safe_name = sanitize_file_name(file_name)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_BILL_EXTENSIONS:
        raise ValidationError(
            "Unsupported file type. Allowed: " + ", ".join(ALLOWED_BILL_EXTENSIONS) + "."
        )
    if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
        raise ValidationError("The uploaded file is empty.")
    if len(file_bytes) > get_settings().max_upload_bytes:
        raise ValidationError("The uploaded file is too large.")
    if not any(bytes(file_bytes[: len(sig)]) == sig for sig in _MAGIC[ext]):
        raise ValidationError("The file content does not match its file type.")
    return safe_name
