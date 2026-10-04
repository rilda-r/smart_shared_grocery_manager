import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

from decimal import Decimal

import pytest

from database.connection import query_one
from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services.bill_service import create_bill
from services.expense_split_service import confirm_bill_split
from services.payment_service import (
    get_room_payments,
    recalculate_balances,
    report_payment,
    settle_payment,
)
from services.room_service import leave_room

DB = database_available_for_tests()
pytestmark = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    prepare_test_database()


@pytest.fixture
def world():
    a, b, c, x = (make_test_user(n) for n in ("alice", "bob", "carol", "mallory"))
    room = make_test_room(a, b, c)["id"]
    bill = create_bill(a, room, items=[
        {"item_name": "Milk", "unit_price": "60.00", "assigned_user_id": b},
        {"item_name": "Bread", "unit_price": "40.00", "assigned_user_id": c},
        {"item_name": "Eggs", "unit_price": "30.00", "assigned_user_id": a},
    ])["data"]
    confirm_bill_split(a, bill["id"])
    pays = {p["payer_user_id"]: p for p in get_room_payments(a, room)["data"]}
    return {"a": a, "b": b, "c": c, "x": x, "room": room, "bill": bill["id"],
            "pay_b": pays[b]["id"], "pay_c": pays[c]["id"]}


def test_payments_have_contract_fields(world):
    p = get_room_payments(world["c"], world["room"])["data"][0]
    assert set(p) == {"id", "room_id", "bill_id", "payer_user_id", "payee_user_id", "amount",
                      "payment_status", "created_at", "settled_at", "reported_at"}
    assert p["payment_status"] == "pending" and p["settled_at"] is None


def test_settle_records_timestamp_and_rejects_duplicate_settlement(world):
    first = settle_payment(world["a"], world["pay_b"])
    assert first["success"] and first["data"]["payment_status"] == "settled"
    assert first["data"]["settled_at"] is not None
    second = settle_payment(world["a"], world["pay_b"])
    assert not second["success"] and second["error_code"] == "duplicate_settlement"
    row = query_one("SELECT settled_at FROM payments WHERE id = %s", (world["pay_b"],))
    assert row["settled_at"] == first["data"]["settled_at"]  # original timestamp preserved


def test_only_payee_can_settle_and_only_payer_can_report(world):
    assert settle_payment(world["b"], world["pay_b"])["error_code"] == "not_authorized"  # payer
    assert settle_payment(world["c"], world["pay_b"])["error_code"] == "not_authorized"  # bystander
    assert report_payment(world["a"], world["pay_b"])["error_code"] == "not_authorized"  # payee
    assert report_payment(world["c"], world["pay_b"])["error_code"] == "not_authorized"


def test_non_members_and_missing_payments(world):
    assert get_room_payments(world["x"], world["room"])["error_code"] == "not_a_member"
    assert settle_payment(world["x"], world["pay_b"])["error_code"] == "payment_not_found"
    assert settle_payment(world["a"], 99999)["error_code"] == "payment_not_found"
    assert report_payment(world["a"], "abc")["error_code"] == "invalid_input"


def test_report_then_settle_flow_and_duplicate_report(world):
    r = report_payment(world["b"], world["pay_b"])
    assert r["success"] and r["data"]["payment_status"] == "reported" and r["data"]["reported_at"]
    assert report_payment(world["b"], world["pay_b"])["error_code"] == "duplicate_report"
    assert settle_payment(world["a"], world["pay_b"])["success"]  # settle from 'reported'
    assert report_payment(world["b"], world["pay_b"])["error_code"] == "duplicate_settlement"


def test_status_filter(world):
    settle_payment(world["a"], world["pay_b"])
    assert len(get_room_payments(world["a"], world["room"], "settled")["data"]) == 1
    assert len(get_room_payments(world["a"], world["room"], "pending")["data"]) == 1
    assert get_room_payments(world["a"], world["room"], "bogus")["error_code"] == "invalid_input"


def test_recalculate_balances_only_counts_unsettled(world):
    def balances():
        r = recalculate_balances(world["a"], world["room"])["data"]
        return {b["user_id"]: b["balance"] for b in r["balances"]}

    assert balances() == {world["a"]: Decimal("100.00"), world["b"]: Decimal("-60.00"),
                          world["c"]: Decimal("-40.00")}
    settle_payment(world["a"], world["pay_b"])
    assert balances() == {world["a"]: Decimal("40.00"), world["b"]: Decimal("0.00"),
                          world["c"]: Decimal("-40.00")}
    assert sum(balances().values()) == 0


def test_split_cannot_be_reconfirmed_after_settlement(world):
    settle_payment(world["a"], world["pay_b"])
    r = confirm_bill_split(world["a"], world["bill"], "equal")
    assert r["error_code"] == "split_already_settled"
    assert len(get_room_payments(world["a"], world["room"])["data"]) == 2  # history intact


def test_leaving_blocked_until_payments_settled(world):
    assert leave_room(world["b"], world["room"])["error_code"] == "outstanding_payments"
    settle_payment(world["a"], world["pay_b"])
    assert leave_room(world["b"], world["room"])["success"]
