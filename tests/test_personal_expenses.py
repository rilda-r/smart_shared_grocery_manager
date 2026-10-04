import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

from datetime import date
from decimal import Decimal

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_user,
    prepare_test_database,
)
from services.personal_expense_service import (
    add_personal_expense,
    calculate_spending_summary,
    delete_personal_expense,
    filter_personal_expenses,
    get_personal_expenses,
    update_personal_expense,
)

DB = database_available_for_tests()
pytestmark = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")

TODAY = date.today().isoformat()


@pytest.fixture(autouse=True)
def fresh_db():
    prepare_test_database()


@pytest.fixture
def users():
    return make_test_user("alice"), make_test_user("bob")


def test_add_returns_contract_fields_and_decimal_money(users):
    a, _ = users
    r = add_personal_expense(a, "12.345", " Food ", TODAY, "  lunch   out ")
    assert r["success"]
    assert set(r["data"]) == {"id", "user_id", "amount", "category", "expense_date",
                              "description", "created_at"}
    assert r["data"]["amount"] == Decimal("12.35") and isinstance(r["data"]["amount"], Decimal)
    assert r["data"]["category"] == "Food" and r["data"]["description"] == "lunch out"
    assert r["data"]["expense_date"] == date.today()


def test_user_a_cannot_access_user_b_expenses(users):
    a, b = users
    mine = add_personal_expense(a, 10, "Food", TODAY)["data"]
    theirs = add_personal_expense(b, 99, "Secret", TODAY, "private")["data"]
    assert [e["id"] for e in get_personal_expenses(a)["data"]] == [mine["id"]]
    assert filter_personal_expenses(a, search="private")["data"] == []
    assert filter_personal_expenses(a, category="Secret")["data"] == []
    assert calculate_spending_summary(a)["data"]["total"] == Decimal("10.00")
    r = update_personal_expense(a, theirs["id"], amount=1)
    assert not r["success"] and r["error_code"] == "expense_not_found"
    assert delete_personal_expense(a, theirs["id"])["error_code"] == "expense_not_found"
    untouched = get_personal_expenses(b)["data"][0]
    assert untouched["amount"] == Decimal("99.00") and untouched["description"] == "private"


def test_unauthenticated_or_bogus_user_ids_rejected(users):
    for bad in (999999, 0, -1, "1", None, True):
        assert not get_personal_expenses(bad)["success"]
        assert not add_personal_expense(bad, 5, "Food", TODAY)["success"]


def test_update_and_delete_own_expense(users):
    a, _ = users
    e = add_personal_expense(a, 10, "Food", TODAY, "x")["data"]
    r = update_personal_expense(a, e["id"], amount="20.50", category="Dining", description=None)
    assert r["data"]["amount"] == Decimal("20.50") and r["data"]["category"] == "Dining"
    assert r["data"]["description"] is None
    assert update_personal_expense(a, e["id"])["error_code"] == "invalid_input"
    assert delete_personal_expense(a, e["id"])["success"]
    assert get_personal_expenses(a)["data"] == []


@pytest.mark.parametrize(
    "amount,category,when",
    [(0, "Food", TODAY), (-5, "Food", TODAY), ("abc", "Food", TODAY), (float("nan"), "Food", TODAY),
     (10 ** 12, "Food", TODAY), (5, "", TODAY), (5, "x" * 51, TODAY), (5, "Food", "31-12-2026"),
     (5, "Food", "1990-01-01"), (5, "Food", None)],
)
def test_invalid_expenses_rejected(users, amount, category, when):
    r = add_personal_expense(users[0], amount, category, when)
    assert not r["success"] and r["error_code"] == "invalid_input"
    assert get_personal_expenses(users[0])["data"] == []


def test_filters_and_summary(users):
    a, _ = users
    for amount, cat, when, desc in [
        ("10.00", "Food", "2026-01-05", "pizza"), ("20.00", "Food", "2026-01-20", "groceries"),
        ("50.00", "Travel", "2026-02-02", "bus pass"), ("5.00", "Fun", "2026-02-10", "100% fun_day"),
    ]:
        assert add_personal_expense(a, amount, cat, when, desc)["success"]
    assert len(filter_personal_expenses(a, category="Food")["data"]) == 2
    assert len(filter_personal_expenses(a, start_date="2026-02-01")["data"]) == 2
    assert len(filter_personal_expenses(a, end_date="2026-01-31", min_amount=15)["data"]) == 1
    assert len(filter_personal_expenses(a, search="bus")["data"]) == 1
    assert len(filter_personal_expenses(a, search="%")["data"]) == 1      # wildcard escaped
    assert len(filter_personal_expenses(a, search="' OR 1=1 --")["data"]) == 0
    s = calculate_spending_summary(a)["data"]
    assert s["total"] == Decimal("85.00") and s["count"] == 4
    assert {c["category"]: c["total"] for c in s["by_category"]} == {
        "Food": Decimal("30.00"), "Travel": Decimal("50.00"), "Fun": Decimal("5.00")}
    assert [(m["month"], m["total"]) for m in s["by_month"]] == [
        ("2026-01", Decimal("30.00")), ("2026-02", Decimal("55.00"))]
    assert calculate_spending_summary(a, end_date="2026-01-31")["data"]["total"] == Decimal("30.00")
