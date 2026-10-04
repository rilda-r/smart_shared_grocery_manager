"""services/personal_expense_service.py - private per-user expenses.

Privacy rule: EVERY query is scoped by ``user_id`` (the authenticated user).
Rows owned by someone else are indistinguishable from rows that do not exist.
"""

from decimal import Decimal

from database.connection import execute, get_cursor, query_all, query_one
from models.personal_expense import PersonalExpense
from services.auth_service import require_user
from utils.helpers import MONEY_QUANT, UNSET, ServiceError, service_call, success_response
from utils.validators import (
    validate_amount,
    validate_category,
    validate_description,
    validate_expense_date,
    validate_id,
)

NOT_FOUND = "Expense not found."


def _public(row: dict) -> dict:
    return PersonalExpense.from_row(row).to_dict()


def _owned(expense_id, user_id, cursor, for_update=False) -> dict:
    validate_id(expense_id, "expense id")
    sql = "SELECT * FROM personal_expenses WHERE id = %s AND user_id = %s"
    row = query_one(sql + (" FOR UPDATE" if for_update else ""), (expense_id, user_id), cursor)
    if row is None:
        raise ServiceError(NOT_FOUND, "expense_not_found")
    return row


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def sum_spending_by_category(user_id, start, end, cursor=None) -> dict:
    """{category: Decimal} for expenses with ``start <= expense_date < end``."""
    rows = query_all(
        "SELECT category, SUM(amount) AS total FROM personal_expenses "
        "WHERE user_id = %s AND expense_date >= %s AND expense_date < %s GROUP BY category",
        (user_id, start, end),
        cursor,
    )
    return {r["category"].lower(): r["total"] for r in rows}


@service_call
def get_personal_expenses(user_id, limit=None, offset=0):
    require_user(user_id)
    sql = "SELECT * FROM personal_expenses WHERE user_id = %s ORDER BY expense_date DESC, id DESC"
    params = [user_id]
    if limit is not None:
        validate_id(limit, "limit")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ServiceError("Invalid offset.", "invalid_input")
        sql += " LIMIT %s OFFSET %s"
        params += [min(limit, 1000), offset]
    return success_response([_public(r) for r in query_all(sql, tuple(params))])


@service_call
def add_personal_expense(user_id, amount, category, expense_date, description=None):
    amount = validate_amount(amount, "Amount")
    category = validate_category(category)
    expense_date = validate_expense_date(expense_date)
    description = validate_description(description)
    with get_cursor() as cur:
        require_user(user_id, cur)
        expense_id = execute(
            "INSERT INTO personal_expenses (user_id, amount, category, expense_date, description) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, amount, category, expense_date, description),
            cur,
        )
        row = query_one("SELECT * FROM personal_expenses WHERE id = %s", (expense_id,), cur)
    return success_response(_public(row), "Expense added.")


@service_call
def update_personal_expense(user_id, expense_id, amount=UNSET, category=UNSET,
                            expense_date=UNSET, description=UNSET):
    changes = {}
    if amount is not UNSET:
        changes["amount"] = validate_amount(amount, "Amount")
    if category is not UNSET:
        changes["category"] = validate_category(category)
    if expense_date is not UNSET:
        changes["expense_date"] = validate_expense_date(expense_date)
    if description is not UNSET:
        changes["description"] = validate_description(description)
    if not changes:
        raise ServiceError("Nothing to update.", "invalid_input")
    with get_cursor() as cur:
        require_user(user_id, cur)
        _owned(expense_id, user_id, cur, for_update=True)
        assignments = ", ".join(f"{col} = %s" for col in changes)  # constant column names
        execute(
            f"UPDATE personal_expenses SET {assignments} WHERE id = %s AND user_id = %s",
            (*changes.values(), expense_id, user_id),
            cur,
        )
        row = query_one(
            "SELECT * FROM personal_expenses WHERE id = %s AND user_id = %s",
            (expense_id, user_id),
            cur,
        )
    return success_response(_public(row), "Expense updated.")


@service_call
def delete_personal_expense(user_id, expense_id):
    with get_cursor() as cur:
        require_user(user_id, cur)
        _owned(expense_id, user_id, cur, for_update=True)
        execute(
            "DELETE FROM personal_expenses WHERE id = %s AND user_id = %s",
            (expense_id, user_id),
            cur,
        )
    return success_response({"id": expense_id}, "Expense deleted.")


def _filters(user_id, category, start_date, end_date, min_amount, max_amount, search):
    clauses, params = ["user_id = %s"], [user_id]
    if category:
        clauses.append("category = %s")
        params.append(validate_category(category))
    if start_date is not None:
        clauses.append("expense_date >= %s")
        params.append(validate_expense_date(start_date))
    if end_date is not None:
        clauses.append("expense_date <= %s")
        params.append(validate_expense_date(end_date))
    if min_amount is not None:
        clauses.append("amount >= %s")
        params.append(validate_amount(min_amount, "Minimum amount", allow_zero=True))
    if max_amount is not None:
        clauses.append("amount <= %s")
        params.append(validate_amount(max_amount, "Maximum amount", allow_zero=True))
    if search:
        clauses.append("(description LIKE %s OR category LIKE %s)")
        params += [_like(str(search).strip()[:100])] * 2
    return " AND ".join(clauses), params


@service_call
def filter_personal_expenses(user_id, category=None, start_date=None, end_date=None,
                             min_amount=None, max_amount=None, search=None):
    require_user(user_id)
    where, params = _filters(user_id, category, start_date, end_date, min_amount, max_amount, search)
    rows = query_all(
        f"SELECT * FROM personal_expenses WHERE {where} ORDER BY expense_date DESC, id DESC",
        tuple(params),
    )
    return success_response([_public(r) for r in rows])


@service_call
def calculate_spending_summary(user_id, start_date=None, end_date=None):
    """Totals overall, by category and by month for the user's own expenses."""
    require_user(user_id)
    where, params = _filters(user_id, None, start_date, end_date, None, None, None)
    overall = query_one(
        f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
        f"FROM personal_expenses WHERE {where}",
        tuple(params),
    )
    by_category = query_all(
        f"SELECT category, SUM(amount) AS total, COUNT(*) AS count FROM personal_expenses "
        f"WHERE {where} GROUP BY category ORDER BY total DESC, category",
        tuple(params),
    )
    by_month = query_all(
        f"SELECT DATE_FORMAT(expense_date, '%%Y-%%m') AS month, SUM(amount) AS total "
        f"FROM personal_expenses WHERE {where} GROUP BY month ORDER BY month",
        tuple(params),
    )
    total = Decimal(overall["total"]).quantize(MONEY_QUANT)
    return success_response(
        {
            "total": total,
            "count": overall["count"],
            "average": (total / overall["count"]).quantize(MONEY_QUANT) if overall["count"] else Decimal("0.00"),
            "by_category": by_category,
            "by_month": by_month,
        }
    )
