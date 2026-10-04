"""
GrocEase utils package.
Combines backend security/validation/helpers with frontend formatting/session utilities.
"""

# Backend helpers & errors
from utils.helpers import (
    MONEY_QUANT,
    ServiceError,
    ValidationError,
    check_upload_size,
    error_response,
    format_iso,
    month_bounds,
    parse_iso,
    service_call,
    success_response,
    to_money,
    utcnow,
)

# Backend security
from utils.security import (
    create_session_token,
    generate_room_code,
    hash_password,
    revoke_session_token,
    verify_password,
    verify_session_token,
)

# Backend validators
from utils.validators import (
    is_valid_room_code_format,
    normalize_room_code,
    password_problems,
    sanitize_file_name,
    validate_amount,
    validate_bill_file,
    validate_bill_quantity,
    validate_category,
    validate_description,
    validate_email,
    validate_expense_date,
    validate_grocery_quantity,
    validate_grocery_status,
    validate_id,
    validate_item_name,
    validate_password,
    validate_room_name,
    validate_username,
)

# Frontend formatting
from utils.formatting import (
    STATUS_BADGE,
    badge_html,
    format_currency,
    format_date,
    format_datetime,
    percentage_color,
)

# Frontend session state management (conditional on Streamlit availability)
try:
    from utils.session import (
        clear_current_room,
        get_current_room_id,
        get_current_room_name,
        get_current_user_id,
        get_username,
        require_auth,
        set_current_room,
        sync_auth_state,
    )
    _session_exports = [
        "sync_auth_state",
        "require_auth",
        "get_current_user_id",
        "get_username",
        "set_current_room",
        "get_current_room_id",
        "get_current_room_name",
        "clear_current_room",
    ]
except ImportError:
    _session_exports = []

__all__ = [
    # Backend helpers
    "success_response",
    "error_response",
    "ServiceError",
    "ValidationError",
    "service_call",
    "to_money",
    "MONEY_QUANT",
    "utcnow",
    "month_bounds",
    "check_upload_size",
    "format_iso",
    "parse_iso",
    # Backend security
    "hash_password",
    "verify_password",
    "create_session_token",
    "verify_session_token",
    "revoke_session_token",
    "generate_room_code",
    # Backend validators
    "validate_id",
    "validate_username",
    "validate_email",
    "validate_password",
    "password_problems",
    "validate_room_name",
    "validate_item_name",
    "validate_category",
    "validate_description",
    "normalize_room_code",
    "is_valid_room_code_format",
    "validate_grocery_status",
    "validate_grocery_quantity",
    "validate_amount",
    "validate_bill_quantity",
    "validate_expense_date",
    "sanitize_file_name",
    "validate_bill_file",
    # Frontend formatting
    "format_currency",
    "format_date",
    "format_datetime",
    "badge_html",
    "percentage_color",
    "STATUS_BADGE",
    # Frontend session
    *_session_exports,
]
