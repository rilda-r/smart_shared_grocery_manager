import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

from decimal import Decimal

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_user,
    prepare_test_database,
)
from services.budget_service import (
    calculate_budget_usage,
    compute_budget_usage,
    create_budget,
    delete_budget,
    get_budgets,
    update_budget,
)
from services.personal_expense_service import add_personal_expense

DB = database_available_for_tests()
needs_db = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")

D = Decimal


@pytest.fixture(autouse=True)
def fresh_db():
    if DB:
        prepare_test_database()


# ------------------------------------------------------------ maths (pure)
def test_usage_under_limit():
    u = compute_budget_usage("200.00", "50.00")
    assert u == {"current_spending": D("50.00"), "remaining_amount": D("150.00"),
                 "percentage_used": D("25.00"), "exceeded": False}


def test_usage_exactly_at_limit_is_not_exceeded():
    u = compute_budget_usage("100.00", "100.00")
    assert u["exceeded"] is False and u["remaining_amount"] == D("0.00") and u["percentage_used"] == D("100.00")


def test_usage_over_limit():
    u = compute_budget_usage("100.00", "125.50")
    assert u["exceeded"] is True and u["remaining_amount"] == D("0.00")
    assert u["percentage_used"] == D("125.50")


def test_usage_rounding_and_zero_spend():
    assert compute_budget_usage("300.00", "100.00")["percentage_used"] == D("33.33")
    assert compute_budget_usage("300.00", None)["current_spending"] == D("0.00")


# ------------------------------------------------------------------ database
@needs_db
def test_create_get_update_delete_budget():
    a = make_test_user("alice")
    b = create_budget(a, " Food ", "250.505")
    assert b["success"] and b["data"]["category"] == "Food" and b["data"]["monthly_limit"] == D("250.51")
    assert set(b["data"]) == {"id", "user_id", "category", "monthly_limit", "created_at", "updated_at"}
    assert [x["id"] for x in get_budgets(a)["data"]] == [b["data"]["id"]]
    u = update_budget(a, b["data"]["id"], monthly_limit=300)
    assert u["data"]["monthly_limit"] == D("300.00")
    assert update_budget(a, b["data"]["id"])["error_code"] == "invalid_input"
    assert delete_budget(a, b["data"]["id"])["success"]
    assert get_budgets(a)["data"] == []


@needs_db
def test_duplicate_category_rejected_case_insensitively():
    a = make_test_user("alice")
    assert create_budget(a, "Food", 100)["success"]
    assert create_budget(a, "food", 200)["error_code"] == "duplicate_budget"
    other = create_budget(a, "Travel", 50)["data"]["id"]
    assert update_budget(a, other, category="FOOD")["error_code"] == "duplicate_budget"


@needs_db
@pytest.mark.parametrize("category,limit", [("", 10), ("Food", 0), ("Food", -1), ("Food", "x"), ("Food", None)])
def test_invalid_budgets_rejected(category, limit):
    a = make_test_user("alice")
    assert create_budget(a, category, limit)["error_code"] == "invalid_input"


@needs_db
def test_budgets_are_private():
    a, b = make_test_user("alice"), make_test_user("bob")
    mine = create_budget(a, "Food", 100)["data"]["id"]
    assert get_budgets(b)["data"] == []
    assert update_budget(b, mine, monthly_limit=1)["error_code"] == "budget_not_found"
    assert delete_budget(b, mine)["error_code"] == "budget_not_found"
    assert get_budgets(a)["data"][0]["monthly_limit"] == D("100.00")
    assert calculate_budget_usage(b)["data"] == []


@needs_db
def test_usage_uses_only_own_spending_in_the_month():
    a, b = make_test_user("alice"), make_test_user("bob")
    create_budget(a, "Food", 100)
    create_budget(a, "Travel", 500)
    add_personal_expense(a, "30.00", "Food", "2026-03-05")
    add_personal_expense(a, "80.00", "food", "2026-03-20")          # case-insensitive category
    add_personal_expense(a, "10.00", "Food", "2026-04-01")          # other month
    add_personal_expense(b, "999.00", "Food", "2026-03-10")         # other user
    usage = {u["category"]: u for u in calculate_budget_usage(a, "2026-03")["data"]}
    food = usage["Food"]
    assert food["current_spending"] == D("110.00") and food["exceeded"] is True
    assert food["remaining_amount"] == D("0.00") and food["percentage_used"] == D("110.00")
    assert food["month"] == "2026-03" and set(food) >= {"budget_id", "category", "monthly_limit"}
    assert usage["Travel"]["current_spending"] == D("0.00") and usage["Travel"]["exceeded"] is False
    assert usage["Travel"]["remaining_amount"] == D("500.00")
    april = {u["category"]: u for u in calculate_budget_usage(a, "2026-04")["data"]}
    assert april["Food"]["current_spending"] == D("10.00")
    assert calculate_budget_usage(a, "03/2026")["error_code"] == "invalid_input"
