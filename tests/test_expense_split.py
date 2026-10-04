import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

import random
from decimal import Decimal

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services.bill_service import (
    assign_bill_item,
    compute_item_matches,
    create_bill,
    get_bill,
    match_bill_items,
    name_similarity,
)
from services.expense_split_service import (
    allocate_proportionally,
    calculate_equal_split,
    calculate_member_shares,
    confirm_bill_split,
)
from services.grocery_service import add_grocery_item
from services.payment_service import get_room_payments

DB = database_available_for_tests()
needs_db = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    if DB:
        prepare_test_database()


def D(value):
    return Decimal(value)


# ------------------------------------------------------- rounding (pure)
def test_allocation_reconciles_exactly_for_awkward_totals():
    shares = allocate_proportionally(D("100.00"), {1: D(1), 2: D(1), 3: D(1)})
    assert sorted(shares.values()) == [D("33.33"), D("33.33"), D("33.34")]
    assert sum(shares.values()) == D("100.00")


def test_allocation_proportional_with_tax():
    shares = allocate_proportionally(D("143.33"), {1: D("30.00"), 2: D("60.00"), 3: D("40.00")})
    assert sum(shares.values()) == D("143.33")
    assert shares[2] > shares[3] > shares[1]


def test_allocation_property_random():
    rng = random.Random(7)
    for _ in range(500):
        total = D(rng.randint(1, 10_000_000)) / 100
        weights = {i: D(rng.randint(1, 100000)) / 100 for i in range(rng.randint(1, 9))}
        shares = allocate_proportionally(total, weights)
        assert sum(shares.values()) == total
        assert all(s >= 0 for s in shares.values())


def test_allocation_ignores_zero_weights_and_rejects_empty():
    assert allocate_proportionally(D("10.00"), {1: D(0), 2: D(5)}) == {2: D("10.00")}
    from utils.helpers import ServiceError
    with pytest.raises(ServiceError):
        allocate_proportionally(D("10.00"), {1: D(0)})


# ------------------------------------------------------ matching (pure)
def test_name_similarity_basics():
    assert name_similarity("Milk", "milk") == 1.0
    assert name_similarity("Amul Milk 1L", "Milk") >= 0.85
    assert name_similarity("Detergent", "Milk") < 0.6


def test_compute_matches_confident_ambiguous_unmatched():
    groceries = [
        {"id": 1, "user_id": 10, "item_name": "Milk", "status": "pending"},
        {"id": 2, "user_id": 10, "item_name": "Rice", "status": "pending"},
        {"id": 3, "user_id": 11, "item_name": "Rice", "status": "pending"},
        {"id": 4, "user_id": 11, "item_name": "Sugar", "status": "unavailable"},
    ]
    bill = [
        {"id": 100, "item_name": "Amul Milk 1L", "assigned_user_id": None},
        {"id": 101, "item_name": "Basmati Rice", "assigned_user_id": None},
        {"id": 102, "item_name": "Detergent", "assigned_user_id": None},
        {"id": 103, "item_name": "Sugar", "assigned_user_id": None},
        {"id": 104, "item_name": "Milk", "assigned_user_id": 11},
    ]
    r = compute_item_matches(bill, groceries)
    assert [(m["bill_item_id"], m["assigned_user_id"]) for m in r["matched"]] == [(100, 10)]
    assert [a["bill_item_id"] for a in r["ambiguous"]] == [101]
    assert {c["user_id"] for c in r["ambiguous"][0]["candidates"]} == {10, 11}
    assert {u["bill_item_id"] for u in r["unmatched"]} == {102, 103}  # unavailable never matched


# ------------------------------------------------------------- DB flows
@pytest.fixture
def world():
    a, b, c, x = (make_test_user(n) for n in ("alice", "bob", "carol", "mallory"))
    room = make_test_room(a, b, c)["id"]
    return {"a": a, "b": b, "c": c, "x": x, "room": room}


def _bill(world, items, total=None, uploader="a"):
    r = create_bill(world[uploader], world["room"], items=items, total_amount=total)
    assert r["success"], r
    return r["data"]


@needs_db
def test_member_shares_reconcile_with_bill_total(world):
    bill = _bill(world, [
        {"item_name": "Milk", "unit_price": "60.00", "assigned_user_id": world["b"]},
        {"item_name": "Bread", "unit_price": "40.00", "assigned_user_id": world["c"]},
        {"item_name": "Eggs", "unit_price": "30.00", "assigned_user_id": world["a"]},
    ], total="143.33")  # includes tax/rounding the items don't show
    r = calculate_member_shares(world["b"], bill["id"])
    assert r["success"] and r["data"]["total_amount"] == D("143.33")
    assert sum(s["amount"] for s in r["data"]["shares"]) == D("143.33")
    by_user = {s["user_id"]: s["amount"] for s in r["data"]["shares"]}
    assert by_user[world["b"]] > by_user[world["c"]] > by_user[world["a"]]
    assert get_bill(world["a"], bill["id"])["data"]["total_amount"] == D("143.33")  # total unchanged


@needs_db
def test_unassigned_items_block_member_wise_split(world):
    bill = _bill(world, [{"item_name": "Mystery", "unit_price": "10.00"},
                         {"item_name": "Milk", "unit_price": "5.00", "assigned_user_id": world["a"]}])
    r = calculate_member_shares(world["a"], bill["id"])
    assert r["error_code"] == "unassigned_items"
    assert r["data"]["unassigned_item_ids"] == [bill["items"][0]["id"]]
    assert confirm_bill_split(world["a"], bill["id"])["error_code"] == "unassigned_items"
    assert get_room_payments(world["a"], world["room"])["data"] == []


@needs_db
def test_matching_assigns_confident_only_and_manual_assignment_resolves_rest(world):
    add_grocery_item(world["b"], world["room"], "Milk")
    add_grocery_item(world["b"], world["room"], "Rice")
    add_grocery_item(world["c"], world["room"], "Rice")
    bill = _bill(world, [
        {"item_name": "Amul Milk 1L", "unit_price": "50.00"},
        {"item_name": "Rice 5kg", "unit_price": "200.00"},
        {"item_name": "Detergent", "unit_price": "90.00"},
    ])
    items = {i["item_name"]: i for i in bill["items"]}
    assert items["Amul Milk 1L"]["assigned_user_id"] == world["b"]
    assert items["Amul Milk 1L"]["matched_grocery_item_id"] is not None
    assert items["Rice 5kg"]["assigned_user_id"] is None       # ambiguous: not silently assigned
    assert items["Detergent"]["assigned_user_id"] is None      # unmatched
    assert len(bill["matching"]["ambiguous"]) == 1 and len(bill["matching"]["unmatched"]) == 1
    assert match_bill_items(world["a"], bill["id"])["data"]["matched"] == []  # still uncertain
    assert assign_bill_item(world["a"], bill["id"], items["Rice 5kg"]["id"], world["c"])["success"]
    assert assign_bill_item(world["a"], bill["id"], items["Detergent"]["id"], world["a"])["success"]
    assert calculate_member_shares(world["a"], bill["id"])["success"]


@needs_db
def test_assign_validations(world):
    bill = _bill(world, [{"item_name": "Milk", "unit_price": "5.00"}])
    item = bill["items"][0]["id"]
    assert assign_bill_item(world["a"], bill["id"], item, world["x"])["error_code"] == "invalid_bill_item"
    assert assign_bill_item(world["a"], bill["id"], 99999, world["b"])["error_code"] == "invalid_bill_item"
    assert assign_bill_item(world["x"], bill["id"], item, world["b"])["error_code"] == "bill_not_found"
    assert assign_bill_item(world["a"], bill["id"], item, world["b"])["success"]
    assert assign_bill_item(world["a"], bill["id"], item, None)["data"]["assigned_user_id"] is None


@needs_db
def test_equal_split_reconciles_and_is_explicit(world):
    bill = _bill(world, [{"item_name": "Pizza", "unit_price": "100.00"}])
    r = calculate_equal_split(world["a"], bill["id"])
    amounts = sorted(s["amount"] for s in r["data"]["shares"])
    assert amounts == [D("33.33"), D("33.33"), D("33.34")] and r["data"]["split_type"] == "equal"
    partial = calculate_equal_split(world["a"], bill["id"], [world["a"], world["b"]])
    assert [s["amount"] for s in partial["data"]["shares"]] == [D("50.00"), D("50.00")]
    assert calculate_equal_split(world["a"], bill["id"], [world["x"]])["error_code"] == "invalid_input"


@needs_db
def test_confirm_split_stores_payments_and_can_be_redone_while_pending(world):
    bill = _bill(world, [
        {"item_name": "Milk", "unit_price": "60.00", "assigned_user_id": world["b"]},
        {"item_name": "Bread", "unit_price": "40.00", "assigned_user_id": world["c"]},
        {"item_name": "Eggs", "unit_price": "30.00", "assigned_user_id": world["a"]},
    ])
    r = confirm_bill_split(world["a"], bill["id"])
    assert r["success"]
    pays = {p["payer_user_id"]: p for p in r["data"]["payments"]}
    assert set(pays) == {world["b"], world["c"]}  # uploader owes nobody
    assert pays[world["b"]]["amount"] == D("60.00") and pays[world["b"]]["payee_user_id"] == world["a"]
    assert pays[world["b"]]["payment_status"] == "pending"
    # Re-confirm as an equal split replaces the pending records (no duplicates).
    again = confirm_bill_split(world["a"], bill["id"], "equal")
    assert len(again["data"]["payments"]) == 2
    # 130.00 / 3: the extra cent goes to the lowest user id (the uploader), so b and c owe 43.33.
    assert sorted(p["amount"] for p in again["data"]["payments"]) == [D("43.33"), D("43.33")]
    assert len(get_room_payments(world["a"], world["room"])["data"]) == 2


@needs_db
def test_confirm_split_permissions_and_validation(world):
    bill = _bill(world, [{"item_name": "Milk", "unit_price": "9.00", "assigned_user_id": world["b"]}])
    assert confirm_bill_split(world["b"], bill["id"])["error_code"] == "not_authorized"
    assert confirm_bill_split(world["x"], bill["id"])["error_code"] == "bill_not_found"
    assert confirm_bill_split(world["a"], bill["id"], "weird")["error_code"] == "invalid_input"
    assert confirm_bill_split(world["a"], 12345)["error_code"] == "bill_not_found"
