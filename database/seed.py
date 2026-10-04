"""
database/seed.py

Schema bootstrap + development/test data helpers.

    python -m database.seed            # create schema only
    python -m database.seed --demo     # create schema + demo users/room

Demo credentials are generated at runtime from environment/random values and
printed once; nothing secret is hard-coded.
"""

import os
import secrets
import sys

from config.settings import get_settings
from database.connection import (
    DatabaseError,
    get_connection,
    init_schema,
)

_TABLES_DROP_ORDER = (
    "payments",
    "bill_items",
    "bills",
    "budgets",
    "personal_expenses",
    "grocery_items",
    "room_members",
    "rooms",
    "users",
)


def prepare_test_database() -> str:
    """Point the process at a ``*_test`` database, create it and wipe all data.

    Refuses to touch any database whose name does not end in ``_test``.
    """
    name = get_settings().db_name
    if not name.endswith("_test"):
        name = f"{name}_test"
        os.environ["GROCEASE_DB_NAME"] = name
    init_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in _TABLES_DROP_ORDER:
            cur.execute(f"TRUNCATE TABLE `{table}`")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        cur.close()
    return name


TEST_PASSWORD = "Str0ng#Pass"


def database_available_for_tests() -> bool:
    """True when a MySQL server accepts the configured credentials."""
    try:
        prepare_test_database()
        return True
    except DatabaseError:
        return False


def make_test_user(username: str) -> int:
    """Register a user through the real service and return its id (test support)."""
    os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")
    from services.auth_service import register_user

    result = register_user(username, f"{username}@example.com", TEST_PASSWORD)
    assert result["success"], result
    return result["data"]["id"]


def make_test_room(owner_id: int, *member_ids: int) -> dict:
    """Create a room owned by ``owner_id`` and join ``member_ids`` (test support)."""
    from services.room_service import create_room, join_room

    room = create_room(owner_id, "Test Flat")
    assert room["success"], room
    for member_id in member_ids:
        assert join_room(member_id, room["data"]["secret_code"])["success"]
    return room["data"]


def seed_demo_data() -> dict:
    """Create two demo users and a shared room. Returns the generated credentials."""
    from services.auth_service import register_user
    from services.room_service import create_room, join_room

    password = "Demo#" + secrets.token_urlsafe(8) + "1a"
    users = []
    for username in ("demo_alice", "demo_bob"):
        result = register_user(username, f"{username}@example.com", password)
        if result["success"]:
            users.append(result["data"])
    if len(users) == 2:
        room = create_room(users[0]["id"], "Demo Flat")
        if room["success"]:
            join_room(users[1]["id"], room["data"]["secret_code"])
    return {"password": password, "users": users}


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    try:
        init_schema()
    except DatabaseError as exc:
        print(f"Schema initialisation failed (errno={exc.errno}).")
        return 1
    print("Schema is up to date.")
    if "--demo" in argv:
        info = seed_demo_data()
        print("Demo users:", [u["username"] for u in info["users"]])
        print("Demo password (shown once):", info["password"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
