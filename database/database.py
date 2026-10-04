"""
database/database.py
Thin MySQL data-access layer for GrocEase user accounts.
"""

import os
from contextlib import contextmanager
from datetime import datetime

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import errorcode

load_dotenv()

DB_HOST = os.environ.get("GROCEASE_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("GROCEASE_DB_PORT", "3306"))
DB_USER = os.environ.get("GROCEASE_DB_USER")
DB_PASSWORD = os.environ.get("GROCEASE_DB_PASSWORD")
DB_NAME = os.environ.get("GROCEASE_DB_NAME", "grocease")


@contextmanager
def get_connection():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


import models


def init_db():
    """Create all application tables and migrations if they don't already exist."""
    try:
        from database.connection import init_schema
        init_schema()
    except Exception:
        pass

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_verified TINYINT(1) NOT NULL DEFAULT 0,
                otp_code VARCHAR(6),
                otp_expires_at VARCHAR(64),
                otp_last_sent_at VARCHAR(64),
                failed_login_attempts INT NOT NULL DEFAULT 0,
                locked_until VARCHAR(64),
                created_at VARCHAR(64) NOT NULL
            )
            """
        )

        # --- Safe migrations for existing databases ---
        migrations = [
            ("locked_until", "VARCHAR(64)"),
        ]
        for column, definition in migrations:
            cursor.execute(f"SHOW COLUMNS FROM users LIKE '{column}'")
            if not cursor.fetchone():
                cursor.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {definition}"
                )
        cursor.close()


def create_user(full_name: str, email: str, password_hash: str) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (full_name.strip(), email.strip().lower(), password_hash,
                 datetime.utcnow().isoformat()),
            )
            cursor.close()
        return True
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            return False
        raise


def get_user_by_email(email: str):
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email = %s", (email.strip().lower(),)
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None


def set_otp(email: str, otp_code: str, expires_at: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET otp_code = %s, otp_expires_at = %s, otp_last_sent_at = %s
            WHERE email = %s
            """,
            (otp_code, expires_at, datetime.utcnow().isoformat(),
             email.strip().lower()),
        )
        cursor.close()


def mark_verified(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET is_verified = 1, otp_code = NULL, otp_expires_at = NULL
            WHERE email = %s
            """,
            (email.strip().lower(),),
        )
        cursor.close()


def clear_otp(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE email = %s",
            (email.strip().lower(),),
        )
        cursor.close()


def record_failed_login(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 "
            "WHERE email = %s",
            (email.strip().lower(),),
        )
        cursor.close()


def reset_failed_login(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL "
            "WHERE email = %s",
            (email.strip().lower(),),
        )
        cursor.close()


def lock_account(email: str, until_iso: str):
    """Locks the account until the given ISO timestamp and resets the counter."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET locked_until = %s, failed_login_attempts = 0 "
            "WHERE email = %s",
            (until_iso, email.strip().lower()),
        )
        cursor.close()


def unlock_account(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET locked_until = NULL WHERE email = %s",
            (email.strip().lower(),),
        )
        cursor.close()


def update_password(email: str, new_password_hash: str):
    """Update password hash (used by Forgot Password flow)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (new_password_hash, email.strip().lower()),
        )
        cursor.close()


def delete_user_account(email: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM users WHERE email = %s",
            (email.strip().lower(),),
        )
        cursor.close()