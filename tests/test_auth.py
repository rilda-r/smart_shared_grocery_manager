import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

import pytest

from database.connection import execute
from database.seed import (
    TEST_PASSWORD,
    database_available_for_tests,
    make_test_user,
    prepare_test_database,
)
from services.auth_service import (
    authenticate_user,
    logout_user,
    register_user,
    validate_login_attempts,
    validate_session,
)
from utils.security import hash_password, verify_password
from utils.validators import password_problems

DB = database_available_for_tests()
needs_db = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")


@pytest.fixture(autouse=True)
def fresh_db():
    if DB:
        prepare_test_database()


# ---------------------------------------------------------------- pure logic
@pytest.mark.parametrize(
    "password",
    ["short1!A", "Str0ng#Pass", "A1!aaaaa"],
)
def test_valid_passwords(password):
    assert password_problems(password) == []


@pytest.mark.parametrize(
    "password",
    ["Sh0rt!", "alllowercase1!", "NoNumbers!!", "NoSpecial123", "", None],
)
def test_invalid_passwords(password):
    assert password_problems(password)


def test_password_hash_is_salted_bcrypt_not_plaintext():
    h1, h2 = hash_password("Str0ng#Pass"), hash_password("Str0ng#Pass")
    assert h1 != h2 and h1.startswith("$2") and "Str0ng#Pass" not in h1
    assert verify_password("Str0ng#Pass", h1)
    assert not verify_password("wrong", h1)


# ------------------------------------------------------------------ database
@needs_db
def test_register_success_never_exposes_hash():
    r = register_user("alice", "Alice@Example.com", TEST_PASSWORD)
    assert r["success"] and r["data"]["email"] == "alice@example.com"
    assert "password_hash" not in r["data"] and TEST_PASSWORD not in str(r)
    assert set(r["data"]) == {"id", "username", "email", "created_at"}


@needs_db
def test_register_rejects_weak_password_bad_email_and_duplicates():
    assert register_user("bob", "bob@example.com", "weak")["error_code"] == "invalid_input"
    assert register_user("bob", "not-an-email", TEST_PASSWORD)["error_code"] == "invalid_input"
    assert register_user("bob", "bob@example.com", TEST_PASSWORD)["success"]
    assert register_user("bob2", "bob@example.com", TEST_PASSWORD)["error_code"] == "duplicate_user"
    assert register_user("bob", "other@example.com", TEST_PASSWORD)["error_code"] == "duplicate_user"


@needs_db
def test_login_by_email_or_username_returns_session():
    make_test_user("carol")
    for identifier in ("carol@example.com", "carol"):
        r = authenticate_user(identifier, TEST_PASSWORD)
        assert r["success"] and "password_hash" not in r["data"]["user"]
    token = r["data"]["session_token"]
    assert validate_session(token)["data"]["username"] == "carol"
    assert logout_user(token)["success"]
    assert validate_session(token)["error_code"] == "unauthorized"
    assert validate_session("garbage")["error_code"] == "unauthorized"


@needs_db
def test_wrong_password_and_unknown_user_look_identical():
    make_test_user("dave")
    wrong = authenticate_user("dave", "Wr0ng#Password")
    ghost = authenticate_user("ghost_user_1", "Wr0ng#Password")
    assert wrong["error_code"] == ghost["error_code"] == "invalid_credentials"
    assert wrong["message"] == ghost["message"]


@needs_db
def test_account_locks_after_three_failures_even_with_correct_password():
    make_test_user("erin")
    for _ in range(3):
        assert authenticate_user("erin", "Wr0ng#Password")["error_code"] == "invalid_credentials"
    locked = authenticate_user("erin", TEST_PASSWORD)
    assert locked["error_code"] == "account_locked" and "30 minutes" in locked["message"]
    assert validate_login_attempts("erin")["data"]["locked"] is True


@needs_db
def test_unknown_identifier_gets_same_lockout_behaviour():
    for _ in range(3):
        authenticate_user("ghost_user_2", "Wr0ng#Password")
    ghost = authenticate_user("ghost_user_2", "Wr0ng#Password")
    make_test_user("frank")
    for _ in range(3):
        authenticate_user("frank", "Wr0ng#Password")
    real = authenticate_user("frank", "Wr0ng#Password")
    assert ghost["error_code"] == real["error_code"] == "account_locked"
    assert ghost["message"] == real["message"]


@needs_db
def test_lock_expires_and_counter_resets_on_success():
    make_test_user("gina")
    for _ in range(3):
        authenticate_user("gina", "Wr0ng#Password")
    execute("UPDATE users SET locked_until = %s WHERE username = 'gina'", ("2000-01-01T00:00:00",))
    assert authenticate_user("gina", TEST_PASSWORD)["success"]
    authenticate_user("gina", "Wr0ng#Password")
    assert authenticate_user("gina", TEST_PASSWORD)["success"]  # counter was reset
