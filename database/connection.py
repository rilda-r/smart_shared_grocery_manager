"""
database/connection.py

MySQL access layer for the GrocEase backend (parameterized SQL only).

Raw driver errors are wrapped in ``DatabaseError`` so they never reach callers
of the service layer. ``legacy`` account code in ``database/database.py`` is
untouched.
"""

import logging
from contextlib import contextmanager
from pathlib import Path

import mysql.connector

from config.settings import get_settings

logger = logging.getLogger("grocease.db")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
ER_DUP_ENTRY = 1062


class DatabaseError(Exception):
    """Wraps any MySQL driver failure. ``errno`` mirrors the driver errno."""

    def __init__(self, message: str = "Database error", errno=None):
        super().__init__(message)
        self.errno = errno

    @property
    def is_duplicate(self) -> bool:
        return self.errno == ER_DUP_ENTRY


def _connect(with_database: bool = True):
    cfg = get_settings()
    params = dict(
        host=cfg.db_host,
        port=cfg.db_port,
        user=cfg.db_user,
        password=cfg.db_password,
        connection_timeout=10,
    )
    if with_database:
        params["database"] = cfg.db_name
    return mysql.connector.connect(**params)


@contextmanager
def get_connection(with_database: bool = True):
    try:
        conn = _connect(with_database)
    except mysql.connector.Error as err:
        raise DatabaseError("Unable to connect", getattr(err, "errno", None)) from err
    try:
        yield conn
    finally:
        try:
            conn.close()
        except mysql.connector.Error:
            pass


@contextmanager
def get_cursor():
    """Transactional dict-cursor: commit on success, rollback on any error."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            yield cursor
            conn.commit()
        except mysql.connector.Error as err:
            conn.rollback()
            raise DatabaseError(str(err.__class__.__name__), getattr(err, "errno", None)) from err
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def query_all(sql: str, params=(), cursor=None) -> list:
    if cursor is not None:
        cursor.execute(sql, params)
        return cursor.fetchall()
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql: str, params=(), cursor=None):
    rows = query_all(sql, params, cursor)
    return rows[0] if rows else None


def execute(sql: str, params=(), cursor=None) -> int:
    """Run a write statement; returns lastrowid (0 if none)."""
    if cursor is not None:
        cursor.execute(sql, params)
        return cursor.lastrowid
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


def database_available() -> bool:
    try:
        with get_connection() as conn:
            return conn.is_connected()
    except DatabaseError:
        return False


def _split_statements(script: str) -> list:
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def _migrate_users_table(cursor) -> None:
    """Bring a pre-existing (legacy) ``users`` table in line with the contract."""
    cursor.execute("SHOW COLUMNS FROM users")
    columns = {row["Field"]: row for row in cursor.fetchall()}
    if "username" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(50) NULL")
        cursor.execute("ALTER TABLE users ADD UNIQUE KEY uq_users_username (username)")
    if "full_name" in columns and columns["full_name"]["Null"] == "NO":
        cursor.execute("ALTER TABLE users MODIFY full_name VARCHAR(255) NULL")
    for col, ddl in (
        ("failed_login_attempts", "INT NOT NULL DEFAULT 0"),
        ("locked_until", "VARCHAR(64) NULL"),
    ):
        if col not in columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    created = str(columns.get("created_at", {}).get("Type", "")).lower()
    if created.startswith("varchar"):
        try:
            cursor.execute(
                "ALTER TABLE users MODIFY created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )
        except mysql.connector.Error:
            logger.warning("Could not convert users.created_at to DATETIME")


def init_schema() -> None:
    """Create the database (if permitted) and apply ``schema.sql`` idempotently."""
    cfg = get_settings()
    try:
        with get_connection(with_database=False) as conn:
            cur = conn.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
            conn.commit()
            cur.close()
        statements = _split_statements(SCHEMA_PATH.read_text(encoding="utf-8"))
        with get_cursor() as cur:
            for statement in statements:
                cur.execute(statement)
            _migrate_users_table(cur)
    except mysql.connector.Error as err:
        raise DatabaseError("Schema initialisation failed", getattr(err, "errno", None)) from err
