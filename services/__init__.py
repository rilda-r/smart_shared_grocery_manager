"""
GrocEase backend services package.
Central export point for all authoritative business logic services.
"""

# Authentication
from services.auth_service import (
    authenticate_user,
    logout_user,
    register_user,
    validate_login_attempts,
    validate_session,
)

# Room Management
from services.room_service import (
    create_room,
    get_room_members,
    get_user_rooms,
    join_room,
    leave_room,
    validate_room_code,
)

# Grocery Management
from services.grocery_service import (
    add_grocery_item,
    delete_grocery_item,
    get_grocery_items,
    update_grocery_item,
)

# Shopping Workflow
from services.shopping_service import (
    finish_shopping,
    get_pending_grocery_items,
    start_shopping,
    update_grocery_item_status,
)

# OCR & Bill Processing
from services.ocr_service import (
    extract_text,
    get_provider,
    parse_bill_items,
    process_bill,
    register_provider,
)
from services.bill_service import (
    assign_bill_item,
    create_bill,
    get_bill,
    match_bill_items,
    update_bill_items,
)

# Expense Splitting & Reconciliation
from services.expense_split_service import (
    calculate_equal_split,
    calculate_member_shares,
    confirm_bill_split,
)

# Payments & Debt Tracking
from services.payment_service import (
    get_room_payments,
    recalculate_balances,
    report_payment,
    settle_payment,
)

# Personal Expenses
from services.personal_expense_service import (
    add_personal_expense,
    calculate_spending_summary,
    delete_personal_expense,
    filter_personal_expenses,
    get_personal_expenses,
    update_personal_expense,
)

# Budgets
from services.budget_service import (
    calculate_budget_usage,
    create_budget,
    delete_budget,
    get_budgets,
    update_budget,
)

__all__ = [
    # Auth
    "register_user",
    "authenticate_user",
    "validate_login_attempts",
    "validate_session",
    "logout_user",
    # Rooms
    "create_room",
    "join_room",
    "get_user_rooms",
    "get_room_members",
    "leave_room",
    "validate_room_code",
    # Grocery
    "add_grocery_item",
    "get_grocery_items",
    "update_grocery_item",
    "delete_grocery_item",
    # Shopping
    "get_pending_grocery_items",
    "start_shopping",
    "update_grocery_item_status",
    "finish_shopping",
    # OCR
    "process_bill",
    "extract_text",
    "parse_bill_items",
    "register_provider",
    "get_provider",
    # Bills
    "create_bill",
    "get_bill",
    "update_bill_items",
    "match_bill_items",
    "assign_bill_item",
    # Expense splitting
    "calculate_member_shares",
    "calculate_equal_split",
    "confirm_bill_split",
    # Payments
    "get_room_payments",
    "settle_payment",
    "report_payment",
    "recalculate_balances",
    # Personal expenses
    "get_personal_expenses",
    "add_personal_expense",
    "update_personal_expense",
    "delete_personal_expense",
    "filter_personal_expenses",
    "calculate_spending_summary",
    # Budgets
    "get_budgets",
    "create_budget",
    "update_budget",
    "delete_budget",
    "calculate_budget_usage",
]
