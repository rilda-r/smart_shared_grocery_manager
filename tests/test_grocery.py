import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services.grocery_service import (
    add_grocery_item,
    delete_grocery_item,
    get_grocery_items,
    update_grocery_item,
)

DB = database_available_for_tests()
pytestmark = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    prepare_test_database()


@pytest.fixture
def world():
    a, b, outsider = (make_test_user(n) for n in ("alice", "bob", "mallory"))
    room = make_test_room(a, b)
    return {"a": a, "b": b, "x": outsider, "room": room["id"]}


def test_add_and_view_items_across_members(world):
    r = add_grocery_item(world["a"], world["room"], "  Milk ", 2)
    assert r["success"] and r["data"]["item_name"] == "Milk" and r["data"]["status"] == "pending"
    assert set(r["data"]) == {"id", "room_id", "user_id", "item_name", "quantity", "status",
                              "created_at", "updated_at"}
    add_grocery_item(world["b"], world["room"], "Eggs")
    seen = get_grocery_items(world["b"], world["room"])["data"]
    assert {i["item_name"] for i in seen} == {"Milk", "Eggs"}  # members view each other's items


def test_user_a_cannot_modify_user_b_item(world):
    item = add_grocery_item(world["b"], world["room"], "Bread")["data"]
    r = update_grocery_item(world["a"], item["id"], item_name="Hacked")
    assert not r["success"] and r["error_code"] == "not_authorized"
    r = update_grocery_item(world["a"], item["id"], status="purchased")
    assert r["error_code"] == "not_authorized"
    assert get_grocery_items(world["a"], world["room"])["data"][0]["item_name"] == "Bread"


def test_user_a_cannot_delete_user_b_item(world):
    item = add_grocery_item(world["b"], world["room"], "Bread")["data"]
    assert delete_grocery_item(world["a"], item["id"])["error_code"] == "not_authorized"
    assert len(get_grocery_items(world["b"], world["room"])["data"]) == 1


def test_owner_can_update_and_delete(world):
    item = add_grocery_item(world["a"], world["room"], "Tea")["data"]
    r = update_grocery_item(world["a"], item["id"], item_name="Green Tea", quantity=3)
    assert r["data"]["item_name"] == "Green Tea" and r["data"]["quantity"] == 3
    assert delete_grocery_item(world["a"], item["id"])["success"]
    assert get_grocery_items(world["a"], world["room"])["data"] == []
    assert delete_grocery_item(world["a"], item["id"])["error_code"] == "not_found"


def test_non_member_cannot_view_add_or_touch_items(world):
    item = add_grocery_item(world["a"], world["room"], "Milk")["data"]
    assert get_grocery_items(world["x"], world["room"])["error_code"] == "not_a_member"
    assert add_grocery_item(world["x"], world["room"], "Spam")["error_code"] == "not_a_member"
    assert update_grocery_item(world["x"], item["id"], quantity=9)["error_code"] == "not_found"
    assert delete_grocery_item(world["x"], item["id"])["error_code"] == "not_found"


def test_validation(world):
    r, a = world["room"], world["a"]
    assert add_grocery_item(a, r, "")["error_code"] == "invalid_input"
    assert add_grocery_item(a, r, "Milk", 0)["error_code"] == "invalid_input"
    assert add_grocery_item(a, r, "Milk", 1.5)["error_code"] == "invalid_input"
    assert add_grocery_item(a, r, "Milk", 1, "bought")["error_code"] == "invalid_input"
    assert update_grocery_item(a, 1)["error_code"] == "invalid_input"


def test_sql_injection_text_is_stored_literally(world):
    evil = "x'); DROP TABLE grocery_items;--"
    assert add_grocery_item(world["a"], world["room"], evil)["success"]
    assert get_grocery_items(world["a"], world["room"])["data"][0]["item_name"] == evil
