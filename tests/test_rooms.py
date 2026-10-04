import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

import pytest

from database.connection import query_one
from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services.room_service import (
    create_room,
    get_room_members,
    get_user_rooms,
    join_room,
    leave_room,
    validate_room_code,
)

DB = database_available_for_tests()
pytestmark = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    prepare_test_database()


def test_create_room_requires_name_and_makes_creator():
    a = make_test_user("alice")
    assert create_room(a, "   ")["error_code"] == "invalid_input"
    r = create_room(a, "Flat 4B")
    assert r["success"] and r["data"]["creator_id"] == a and r["data"]["role"] == "creator"
    assert len(r["data"]["secret_code"]) == 8


def test_room_codes_are_unique():
    a = make_test_user("alice")
    codes = {create_room(a, f"Room {i}")["data"]["secret_code"] for i in range(15)}
    assert len(codes) == 15


def test_invalid_room_codes_rejected():
    b = make_test_user("bob")
    for bad in ("", "short", "ZZZZZZZZ", "AAAA AAAA", None, "'; DROP TABLE rooms;--"):
        assert join_room(b, bad)["error_code"] == "invalid_room_code"
        assert validate_room_code(bad)["error_code"] == "invalid_room_code"


def test_join_valid_code_case_insensitive_and_duplicate_membership_blocked():
    a, b = make_test_user("alice"), make_test_user("bob")
    code = create_room(a, "Flat")["data"]["secret_code"]
    assert validate_room_code(code.lower())["success"]
    assert join_room(b, code.lower())["success"]
    assert join_room(b, code)["error_code"] == "duplicate_membership"
    assert join_room(a, code)["error_code"] == "duplicate_membership"
    assert query_one("SELECT COUNT(*) AS c FROM room_members")["c"] == 2


def test_get_user_rooms_only_returns_own_rooms():
    a, b, c = (make_test_user(n) for n in ("alice", "bob", "carol"))
    room = make_test_room(a, b)
    assert [r["id"] for r in get_user_rooms(b)["data"]] == [room["id"]]
    assert get_user_rooms(c)["data"] == []


def test_member_list_requires_membership():
    a, b, c = (make_test_user(n) for n in ("alice", "bob", "carol"))
    room = make_test_room(a, b)
    assert len(get_room_members(a, room["id"])["data"]) == 2
    assert get_room_members(c, room["id"])["error_code"] == "not_a_member"


def test_leave_room_member_creator_transfer_and_last_member():
    a, b = make_test_user("alice"), make_test_user("bob")
    room = make_test_room(a, b)
    assert leave_room(a, room["id"])["success"]  # creator leaves -> bob inherits
    assert query_one("SELECT creator_id FROM rooms WHERE id = %s", (room["id"],))["creator_id"] == b
    assert query_one("SELECT role FROM room_members WHERE user_id = %s", (b,))["role"] == "creator"
    assert leave_room(a, room["id"])["error_code"] == "not_a_member"
    assert leave_room(b, room["id"])["success"]  # last member -> room removed
    assert query_one("SELECT id FROM rooms WHERE id = %s", (room["id"],)) is None
