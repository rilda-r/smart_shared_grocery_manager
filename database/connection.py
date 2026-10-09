"""
database/connection.py

Supabase PostgreSQL access layer for the GrocEase backend (parameterized SQL only).

Uses psycopg2 with RealDictCursor. Raw driver errors are wrapped in ``DatabaseError``
so they never reach callers of the service layer.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import get_settings

logger = logging.getLogger("grocease.db")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
PG_UNIQUE_VIOLATION = "23505"
ER_DUP_ENTRY = 1062


class DatabaseError(Exception):
    """Wraps database driver failures. ``errno`` and ``pgcode`` mirror driver codes."""

    def __init__(self, message: str = "Database error", errno=None, pgcode=None):
        super().__init__(message)
        self.errno = errno
        self.pgcode = pgcode

    @property
    def is_duplicate(self) -> bool:
        return self.errno == ER_DUP_ENTRY or self.pgcode == PG_UNIQUE_VIOLATION


def _connect():
    cfg = get_settings()

    # If full connection URL / DSN is provided (Supabase pooler or direct connection)
    if cfg.db_url:
        return psycopg2.connect(cfg.db_url, cursor_factory=RealDictCursor)

    params = dict(
        host=cfg.db_host,
        port=cfg.db_port,
        user=cfg.db_user,
        password=cfg.db_password,
        dbname=cfg.db_name,
        connect_timeout=10,
        cursor_factory=RealDictCursor,
    )

    sslmode = os.environ.get("GROCEASE_DB_SSLMODE") or cfg.db_sslmode
    if sslmode:
        params["sslmode"] = sslmode
    elif cfg.db_host not in ("localhost", "127.0.0.1", ""):
        # Default to requiring SSL for cloud-hosted Supabase
        params["sslmode"] = "require"

    return psycopg2.connect(**params)


@contextmanager
def get_connection(with_database: bool = True):
    try:
        conn = _connect()
    except psycopg2.Error as err:
        pgcode = getattr(err, "pgcode", None)
        raise DatabaseError("Unable to connect to database: " + str(err), pgcode=pgcode) from err
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_cursor():
    """Transactional dict-cursor: commit on success, rollback on any error."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except psycopg2.Error as err:
            conn.rollback()
            pgcode = getattr(err, "pgcode", None)
            raise DatabaseError(str(err), pgcode=pgcode) from err
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass


def query_all(sql: str, params=(), cursor=None) -> list:
    if cursor is not None:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) if hasattr(r, "keys") else r for r in rows]
    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) if hasattr(r, "keys") else r for r in rows]


def query_one(sql: str, params=(), cursor=None):
    rows = query_all(sql, params, cursor)
    return rows[0] if rows else None


def execute(sql: str, params=(), cursor=None) -> int:
    """Run a write statement; returns lastrowid/generated id (0 if none)."""
    sql_stripped = sql.strip()
    is_insert = sql_stripped.upper().startswith("INSERT")
    has_returning = "RETURNING" in sql_stripped.upper()

    final_sql = sql
    expect_returning = has_returning
    if is_insert and not has_returning:
        parts = sql_stripped.split()
        table_name = ""
        for i, p in enumerate(parts):
            if p.upper() == "INTO" and i + 1 < len(parts):
                table_name = parts[i + 1].strip('"`()').lower()
                break
        if table_name in ("room_members", "profiles"):
            final_sql = sql_stripped
            expect_returning = False
        else:
            final_sql = f"{sql_stripped} RETURNING id"
            expect_returning = True

    if cursor is not None:
        cursor.execute(final_sql, params)
        if expect_returning:
            try:
                row = cursor.fetchone()
                if row:
                    return row["id"] if isinstance(row, dict) and "id" in row else (row[0] if row else 0)
            except Exception:
                return 0
        return cursor.rowcount or 0

    with get_cursor() as cur:
        cur.execute(final_sql, params)
        if expect_returning:
            try:
                row = cur.fetchone()
                if row:
                    return row["id"] if isinstance(row, dict) and "id" in row else (row[0] if row else 0)
            except Exception:
                return 0
        return cur.rowcount or 0


def database_available() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception:
        return False


def _split_statements(script: str) -> list:
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def _migrate_users_table(cursor) -> None:
    """Idempotently bring users table in line with current contract."""
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR(6) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at VARCHAR(64) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_last_sent_at VARCHAR(64) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until VARCHAR(64) NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50) NULL",
        """CREATE TABLE IF NOT EXISTS profiles (
            user_id INT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            nickname VARCHAR(50) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )""",
        "ALTER TABLE grocery_items ADD COLUMN IF NOT EXISTS purchased_quantity INT NOT NULL DEFAULT 0",
        """CREATE TABLE IF NOT EXISTS monthly_budget_history (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            month_year VARCHAR(7) NOT NULL,
            total_budget DECIMAL(10,2) NOT NULL,
            total_spent DECIMAL(10,2) NOT NULL,
            total_saved DECIMAL(10,2) NOT NULL,
            category_breakdown JSONB NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_month_history UNIQUE (user_id, month_year),
            CONSTRAINT fk_budget_hist_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_budget_hist_user ON monthly_budget_history (user_id)",
    ]

    for m in migrations:
        try:
            cursor.execute(m)
        except Exception as exc:
            logger.warning(f"Migration step ignored: {exc}")


def init_schema() -> None:
    """Apply ``schema.sql`` idempotently on Supabase PostgreSQL."""
    statements = _split_statements(SCHEMA_PATH.read_text(encoding="utf-8"))
    with get_cursor() as cur:
        for statement in statements:
            try:
                cur.execute(statement)
            except Exception as e:
                logger.warning(f"Schema statement warning: {e}")
        _migrate_users_table(cur)
