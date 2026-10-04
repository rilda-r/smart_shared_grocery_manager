import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services.grocery_service import add_grocery_item, get_grocery_items
from services.shopping_service import (
    finish_shopping,
    get_pending_grocery_items,
    start_shopping,
    update_grocery_item_status,
)

DB = database_available_for_tests()
pytestmark = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    prepare_test_database()


@pytest.fixture
def world():
    a, b, x = (make_test_user(n) for n in ("alice", "bob", "mallory"))
    room = make_test_room(a, b)["id"]
    ids = {n: add_grocery_item(u, room, n)["data"]["id"]
           for n, u in (("Milk", a), ("Eggs", b), ("Rice", a))}
    return {"a": a, "b": b, "x": x, "room": room, "ids": ids}


def test_start_shopping_lists_pending_only(world):
    update_grocery_item_status(world["a"], world["ids"]["Milk"], "purchased")
    r = start_shopping(world["b"], world["room"])
    assert r["success"] and {i["item_name"] for i in r["data"]["items"]} == {"Eggs", "Rice"}
    assert {i["item_name"] for i in get_pending_grocery_items(world["a"], world["room"])["data"]} == {"Eggs", "Rice"}


def test_status_changes_are_persisted_by_any_member(world):
    r = update_grocery_item_status(world["b"], world["ids"]["Milk"], "purchased")  # alice's item
    assert r["success"] and r["data"]["status"] == "purchased"
    update_grocery_item_status(world["a"], world["ids"]["Eggs"], "unavailable")
    status = {i["item_name"]: i["status"] for i in get_grocery_items(world["a"], world["room"])["data"]}
    assert status == {"Milk": "purchased", "Eggs": "unavailable", "Rice": "pending"}


def test_status_can_be_reverted_to_pending(world):
    update_grocery_item_status(world["a"], world["ids"]["Milk"], "purchased")
    assert update_grocery_item_status(world["a"], world["ids"]["Milk"], "pending")["success"]


def test_invalid_status_rejected(world):
    r = update_grocery_item_status(world["a"], world["ids"]["Milk"], "bought")
    assert r["error_code"] == "invalid_input"
    assert get_grocery_items(world["a"], world["room"], "pending")["data"][0]["status"] == "pending"


def test_finish_shopping_summary(world):
    update_grocery_item_status(world["a"], world["ids"]["Milk"], "purchased")
    update_grocery_item_status(world["a"], world["ids"]["Eggs"], "unavailable")
    r = finish_shopping(world["a"], world["room"])
    assert r["data"]["counts"] == {"purchased": 1, "unavailable": 1, "pending": 1}


def test_non_members_blocked_from_shopping_data(world):
    x, room = world["x"], world["room"]
    assert start_shopping(x, room)["error_code"] == "not_a_member"
    assert get_pending_grocery_items(x, room)["error_code"] == "not_a_member"
    assert finish_shopping(x, room)["error_code"] == "not_a_member"
    assert update_grocery_item_status(x, world["ids"]["Milk"], "purchased")["error_code"] == "not_found"
