"""services/budget_service.py - private monthly category budgets and usage."""

from datetime import date, datetime
from decimal import Decimal

from database.connection import DatabaseError, execute, get_cursor, query_all, query_one
from models.budget import Budget
from services.auth_service import require_user
from services.personal_expense_service import sum_spending_by_category
from utils.helpers import (
    MONEY_QUANT,
    UNSET,
    ServiceError,
    month_bounds,
    service_call,
    success_response,
)
from utils.validators import validate_amount, validate_category, validate_id

DUPLICATE_MESSAGE = "You already have a budget for that category."


def _public(row: dict) -> dict:
    return Budget.from_row(row).to_dict()


def compute_budget_usage(monthly_limit, spent) -> dict:
    """Pure budget maths (Decimal)."""
    limit = Decimal(monthly_limit).quantize(MONEY_QUANT)
    spent = Decimal(spent or 0).quantize(MONEY_QUANT)
    remaining = max(limit - spent, Decimal("0.00"))
    percentage = (spent * 100 / limit).quantize(MONEY_QUANT) if limit > 0 else Decimal("0.00")
    return {
        "current_spending": spent,
        "remaining_amount": remaining,
        "percentage_used": percentage,
        "exceeded": spent > limit,
    }


def _parse_month(month):
    if month is None:
        today = date.today()
        return today.year, today.month
    if isinstance(month, (date, datetime)):
        return month.year, month.month
    try:
        parsed = datetime.strptime(str(month).strip(), "%Y-%m")
        return parsed.year, parsed.month
    except ValueError:
        raise ServiceError("Month must be in YYYY-MM format.", "invalid_input")


def _owned(budget_id, user_id, cursor, for_update=False) -> dict:
    validate_id(budget_id, "budget id")
    sql = "SELECT * FROM budgets WHERE id = %s AND user_id = %s"
    row = query_one(sql + (" FOR UPDATE" if for_update else ""), (budget_id, user_id), cursor)
    if row is None:
        raise ServiceError("Budget not found.", "budget_not_found")
    return row


@service_call
def get_budgets(user_id):
    require_user(user_id)
    rows = query_all("SELECT * FROM budgets WHERE user_id = %s ORDER BY category", (user_id,))
    return success_response([_public(r) for r in rows])


@service_call
def create_budget(user_id, category, monthly_limit):
    category = validate_category(category)
    monthly_limit = validate_amount(monthly_limit, "Monthly limit")
    try:
        with get_cursor() as cur:
            require_user(user_id, cur)
            budget_id = execute(
                "INSERT INTO budgets (user_id, category, monthly_limit) VALUES (%s, %s, %s)",
                (user_id, category, monthly_limit),
                cur,
            )
            row = query_one("SELECT * FROM budgets WHERE id = %s", (budget_id,), cur)
    except DatabaseError as exc:
        if exc.is_duplicate:
            raise ServiceError(DUPLICATE_MESSAGE, "duplicate_budget")
        raise
    return success_response(_public(row), "Budget created.")


@service_call
def update_budget(user_id, budget_id, category=UNSET, monthly_limit=UNSET):
    changes = {}
    if category is not UNSET:
        changes["category"] = validate_category(category)
    if monthly_limit is not UNSET:
        changes["monthly_limit"] = validate_amount(monthly_limit, "Monthly limit")
    if not changes:
        raise ServiceError("Nothing to update.", "invalid_input")
    try:
        with get_cursor() as cur:
            require_user(user_id, cur)
            _owned(budget_id, user_id, cur, for_update=True)
            assignments = ", ".join(f"{col} = %s" for col in changes)  # constant column names
            execute(
                f"UPDATE budgets SET {assignments} WHERE id = %s AND user_id = %s",
                (*changes.values(), budget_id, user_id),
                cur,
            )
            row = query_one(
                "SELECT * FROM budgets WHERE id = %s AND user_id = %s", (budget_id, user_id), cur
            )
    except DatabaseError as exc:
        if exc.is_duplicate:
            raise ServiceError(DUPLICATE_MESSAGE, "duplicate_budget")
        raise
    return success_response(_public(row), "Budget updated.")


@service_call
def delete_budget(user_id, budget_id):
    with get_cursor() as cur:
        require_user(user_id, cur)
        _owned(budget_id, user_id, cur, for_update=True)
        execute("DELETE FROM budgets WHERE id = %s AND user_id = %s", (budget_id, user_id), cur)
    return success_response({"id": budget_id}, "Budget deleted.")


@service_call
def calculate_budget_usage(user_id, month=None):
    """Usage of each of the user's budgets for ``month`` ("YYYY-MM" / date; default: now)."""
    year, month_number = _parse_month(month)
    start, end = month_bounds(year, month_number)
    with get_cursor() as cur:
        require_user(user_id, cur)
        budgets = query_all("SELECT * FROM budgets WHERE user_id = %s ORDER BY category", (user_id,), cur)
        spending = sum_spending_by_category(user_id, start, end, cur)
    usage = []
    for budget in budgets:
        spent = spending.get(budget["category"].lower(), Decimal("0.00"))
        usage.append(
            {
                "budget_id": budget["id"],
                "category": budget["category"],
                "monthly_limit": budget["monthly_limit"],
                "month": f"{year:04d}-{month_number:02d}",
                **compute_budget_usage(budget["monthly_limit"], spent),
            }
        )
    return success_response(usage)
