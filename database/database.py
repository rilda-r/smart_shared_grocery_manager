"""
database/database.py

Supabase PostgreSQL data-access layer for GrocEase user accounts, profiles,
rooms, and cascading operations.
"""

from datetime import datetime
import json

from database.connection import (
    DatabaseError,
    execute,
    get_connection,
    get_cursor,
    init_schema,
    query_all,
    query_one,
)


_DB_INITIALIZED = False


def init_db(force: bool = False):
    """Ensure database schema and user columns are initialized on Supabase PostgreSQL (runs once per process)."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED and not force:
        return
    init_schema()
    _DB_INITIALIZED = True


def update_unverified_user(full_name: str, email: str, password_hash: str) -> bool:
    """Updates password and profile for an unverified user attempting registration again."""
    clean_email = email.strip().lower()
    execute(
        """
        UPDATE users
        SET full_name = %s, password_hash = %s, failed_login_attempts = 0, locked_until = NULL
        WHERE LOWER(email) = %s AND is_verified = FALSE
        """,
        (full_name.strip(), password_hash, clean_email),
    )
    user = query_one("SELECT id FROM users WHERE LOWER(email) = %s", (clean_email,))
    if user:
        try:
            execute(
                """
                INSERT INTO profiles (user_id, full_name, nickname, created_at, updated_at)
                VALUES (%s, %s, NULL, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET full_name = EXCLUDED.full_name, updated_at = EXCLUDED.updated_at
                """,
                (user["id"], full_name.strip(), datetime.utcnow(), datetime.utcnow()),
            )
        except Exception:
            pass
    return True


def create_user(full_name: str, email: str, password_hash: str) -> bool:
    try:
        user_id = execute(
            """
            INSERT INTO users (full_name, email, password_hash, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                full_name.strip(),
                email.strip().lower(),
                password_hash,
                datetime.utcnow(),
            ),
        )
        if user_id:
            try:
                execute(
                    """
                    INSERT INTO profiles (user_id, full_name, nickname, created_at, updated_at)
                    VALUES (%s, %s, NULL, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (user_id, full_name.strip(), datetime.utcnow(), datetime.utcnow()),
                )
            except Exception:
                pass
        return True
    except DatabaseError as err:
        if err.is_duplicate:
            return False
        raise


def get_user_by_email(email: str):
    if not email:
        return None
    return query_one(
        """
        SELECT u.*, COALESCE(p.nickname, u.nickname) AS profile_nickname
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE LOWER(u.email) = %s
        """,
        (email.strip().lower(),),
    )


def get_user_by_id(user_id: int):
    if not user_id:
        return None
    return query_one(
        """
        SELECT u.*, COALESCE(p.nickname, u.nickname) AS profile_nickname
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE u.id = %s
        """,
        (int(user_id),),
    )


def get_profile(user_id: int):
    """Fetch user identity: both Actual Name and dynamic Nickname."""
    if not user_id:
        return None
    row = query_one(
        """
        SELECT u.id AS user_id, u.email, u.full_name AS actual_name,
               COALESCE(p.nickname, u.nickname) AS nickname,
               u.created_at
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE u.id = %s
        """,
        (int(user_id),),
    )
    return row


def update_nickname(user_id: int, nickname: str) -> bool:
    """Securely store dynamic Nickname in Supabase profiles and users tables."""
    nick = nickname.strip()
    now = datetime.utcnow()
    # Upsert into profiles
    try:
        execute(
            """
            INSERT INTO profiles (user_id, full_name, nickname, created_at, updated_at)
            VALUES (%s, (SELECT full_name FROM users WHERE id = %s), %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET nickname = EXCLUDED.nickname, updated_at = EXCLUDED.updated_at
            """,
            (user_id, user_id, nick, now, now),
        )
    except Exception:
        pass

    # Update users table
    execute(
        "UPDATE users SET nickname = %s, username = %s WHERE id = %s",
        (nick, nick, int(user_id)),
    )
    return True


def set_otp(email: str, otp_code: str, expires_at: str):
    execute(
        """
        UPDATE users
        SET otp_code = %s, otp_expires_at = %s, otp_last_sent_at = %s
        WHERE LOWER(email) = %s
        """,
        (
            otp_code,
            expires_at,
            datetime.utcnow().isoformat(),
            email.strip().lower(),
        ),
    )


def mark_verified(email: str):
    execute(
        """
        UPDATE users
        SET is_verified = TRUE, otp_code = NULL, otp_expires_at = NULL
        WHERE LOWER(email) = %s
        """,
        (email.strip().lower(),),
    )


def clear_otp(email: str):
    execute(
        """
        UPDATE users
        SET otp_code = NULL, otp_expires_at = NULL
        WHERE LOWER(email) = %s
        """,
        (email.strip().lower(),),
    )


def record_failed_login(email: str):
    execute(
        """
        UPDATE users
        SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1
        WHERE LOWER(email) = %s
        """,
        (email.strip().lower(),),
    )


def reset_failed_login(email: str):
    execute(
        """
        UPDATE users
        SET failed_login_attempts = 0, locked_until = NULL
        WHERE LOWER(email) = %s
        """,
        (email.strip().lower(),),
    )


def lock_account(email: str, until_iso: str):
    """Locks the account until the given ISO timestamp and resets the counter."""
    execute(
        """
        UPDATE users
        SET locked_until = %s, failed_login_attempts = 0
        WHERE LOWER(email) = %s
        """,
        (until_iso, email.strip().lower()),
    )


def unlock_account(email: str):
    execute(
        """
        UPDATE users
        SET locked_until = NULL
        WHERE LOWER(email) = %s
        """,
        (email.strip().lower(),),
    )


def update_password(email: str, new_password_hash: str):
    """Update password hash (used by Password Reset flow)."""
    execute(
        """
        UPDATE users
        SET password_hash = %s
        WHERE LOWER(email) = %s
        """,
        (new_password_hash, email.strip().lower()),
    )


def delete_user_account(user_identifier):
    """
    Cascading account deletion: removes user record and all associated DB rows
    (profiles, room memberships, created rooms, payments, expenses, budgets).
    """
    if isinstance(user_identifier, int) or (isinstance(user_identifier, str) and user_identifier.isdigit()):
        user = query_one("SELECT * FROM users WHERE id = %s", (int(user_identifier),))
    else:
        user = query_one("SELECT * FROM users WHERE LOWER(email) = %s", (str(user_identifier).strip().lower(),))

    if not user:
        return False

    uid = user["id"]

    with get_cursor() as cur:
        # Delete related payments
        execute("DELETE FROM payments WHERE payer_user_id = %s OR payee_user_id = %s", (uid, uid), cur)

        # Delete bill items for bills uploaded by user or assigned to user
        execute(
            """
            DELETE FROM bill_items 
            WHERE bill_id IN (SELECT id FROM bills WHERE uploaded_by = %s)
               OR assigned_user_id = %s
            """,
            (uid, uid),
            cur,
        )

        # Delete bills uploaded by user
        execute("DELETE FROM bills WHERE uploaded_by = %s", (uid,), cur)

        # Delete user's grocery items
        execute("DELETE FROM grocery_items WHERE user_id = %s", (uid,), cur)

        # Delete room memberships
        execute("DELETE FROM room_members WHERE user_id = %s", (uid,), cur)

        # Delete rooms created by user (and any remaining children)
        execute("DELETE FROM rooms WHERE creator_id = %s", (uid,), cur)

        # Delete personal expenses
        execute("DELETE FROM personal_expenses WHERE user_id = %s", (uid,), cur)

        # Delete budgets
        execute("DELETE FROM budgets WHERE user_id = %s", (uid,), cur)

        # Delete profile
        execute("DELETE FROM profiles WHERE user_id = %s", (uid,), cur)

        # Finally delete user
        execute("DELETE FROM users WHERE id = %s", (uid,), cur)

    return True


def get_user_joined_rooms(user_id: int) -> list:
    """Retrieve all rooms the user has joined from the database."""
    if not user_id:
        return []
    try:
        return query_all(
            """
            SELECT r.id, r.name, r.secret_code, m.role, r.created_at
            FROM rooms r
            JOIN room_members m ON m.room_id = r.id
            WHERE m.user_id = %s
            ORDER BY r.name ASC
            """,
            (int(user_id),),
        )
    except Exception:
        return []


def get_room_members_with_identities(room_id: int) -> list:
    """Query database to get actual nicknames/usernames for all room members."""
    if not room_id:
        return []
    try:
        return query_all(
            """
            SELECT m.user_id, m.role, m.joined_at,
                   COALESCE(NULLIF(p.nickname, ''), NULLIF(u.nickname, ''), NULLIF(u.username, ''), NULLIF(u.full_name, ''), 'Member') AS display_name,
                   u.full_name AS actual_name,
                   u.email
            FROM room_members m
            JOIN users u ON u.id = m.user_id
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE m.room_id = %s
            ORDER BY m.joined_at ASC
            """,
            (int(room_id),),
        )
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# PHASE 3: LIVE GROCERY SYNC & ATTRIBUTION
# ─────────────────────────────────────────────────────────────

def get_live_grocery_items(room_id: int) -> list:
    """Fetch all grocery items for a room joined with user/profile nicknames for live attribution."""
    if not room_id:
        return []
    try:
        rows = query_all(
            """
            SELECT g.id, g.room_id, g.user_id, g.item_name, g.quantity,
                   COALESCE(g.purchased_quantity, 0) AS purchased_quantity,
                   g.status, g.created_at, g.updated_at,
                   COALESCE(NULLIF(p.nickname, ''), NULLIF(u.nickname, ''), NULLIF(u.username, ''), NULLIF(u.full_name, ''), 'Member') AS added_by_name,
                   u.email AS user_email
            FROM grocery_items g
            LEFT JOIN users u ON u.id = g.user_id
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE g.room_id = %s
            ORDER BY g.created_at ASC, g.id ASC
            """,
            (int(room_id),),
        )
        return [
            {
                "id": r["id"],
                "roomId": r["room_id"],
                "userId": r["user_id"],
                "itemName": r["item_name"],
                "quantity": r["quantity"],
                "purchasedQuantity": r.get("purchased_quantity", 0) or 0,
                "status": r["status"],
                "createdAt": str(r.get("created_at") or ""),
                "updatedAt": str(r.get("updated_at") or ""),
                "addedByName": r.get("added_by_name", "Member"),
                "userEmail": r.get("user_email", ""),
            }
            for r in rows
        ]
    except Exception:
        return []


def add_live_grocery_item(room_id: int, user_id: int, item_name: str, quantity: int) -> dict:
    """Insert a new grocery item into Supabase PostgreSQL."""
    now = datetime.utcnow()
    item_id = execute(
        """
        INSERT INTO grocery_items (room_id, user_id, item_name, quantity, purchased_quantity, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 0, 'pending', %s, %s)
        """,
        (int(room_id), int(user_id), item_name.strip(), int(quantity), now, now),
    )
    return {
        "id": item_id,
        "roomId": int(room_id),
        "userId": int(user_id),
        "itemName": item_name.strip(),
        "quantity": int(quantity),
        "purchasedQuantity": 0,
        "status": "pending",
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat(),
    }


def increment_grocery_item_quantity(item_id: int, add_qty: int) -> bool:
    """Increase quantity linearly when user confirms adding upon an existing duplicate item."""
    execute(
        """
        UPDATE grocery_items
        SET quantity = quantity + %s, updated_at = %s
        WHERE id = %s
        """,
        (int(add_qty), datetime.utcnow(), int(item_id)),
    )
    return True


def update_live_grocery_item(item_id: int, item_name: str, quantity: int) -> bool:
    """Update item name and quantity only if not already purchased."""
    execute(
        """
        UPDATE grocery_items
        SET item_name = %s, quantity = %s, updated_at = %s
        WHERE id = %s AND status <> 'purchased'
        """,
        (item_name.strip(), int(quantity), datetime.utcnow(), int(item_id)),
    )
    return True


def delete_live_grocery_item(item_id: int) -> bool:
    """Delete a grocery item if not purchased."""
    execute(
        "DELETE FROM grocery_items WHERE id = %s AND status <> 'purchased'",
        (int(item_id),),
    )
    return True


def mark_grocery_item_purchased_live(item_id: int, increment: int = 1) -> bool:
    """
    Incrementally marks item purchases in Supabase. Each action increments purchased_quantity.
    Only when purchased_quantity >= total quantity does status become 'purchased'.
    """
    execute(
        """
        UPDATE grocery_items
        SET purchased_quantity = GREATEST(0, COALESCE(purchased_quantity, 0) + %s),
            status = CASE 
                WHEN GREATEST(0, COALESCE(purchased_quantity, 0) + %s) >= quantity THEN 'purchased'
                ELSE 'pending'
            END,
            updated_at = %s
        WHERE id = %s
        """,
        (int(increment), int(increment), datetime.utcnow(), int(item_id)),
    )
    return True


def reset_grocery_item_purchased_live(item_id: int) -> bool:
    """Reset purchased quantity to 0 and status to pending."""
    execute(
        """
        UPDATE grocery_items
        SET purchased_quantity = 0, status = 'pending', updated_at = %s
        WHERE id = %s
        """,
        (datetime.utcnow(), int(item_id)),
    )
    return True


def update_grocery_item_status_live(item_id: int, status: str) -> bool:
    """Update status of a grocery item (pending/purchased/unavailable)."""
    execute(
        """
        UPDATE grocery_items
        SET status = %s, updated_at = %s
        WHERE id = %s
        """,
        (status, datetime.utcnow(), int(item_id)),
    )
    return True


# ─────────────────────────────────────────────────────────────
# PHASE 3: MONTHLY BUDGET HISTORY & ARCHIVING
# ─────────────────────────────────────────────────────────────

def save_monthly_budget_history(
    user_id: int,
    month_year: str,
    total_budget: float,
    total_spent: float,
    total_saved: float,
    category_breakdown: dict = None,
) -> bool:
    """Saves a static month-end budget report forever in Supabase monthly_budget_history table."""
    now = datetime.utcnow()
    json_breakdown = json.dumps(category_breakdown or {})
    execute(
        """
        INSERT INTO monthly_budget_history
            (user_id, month_year, total_budget, total_spent, total_saved, category_breakdown, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, month_year) DO UPDATE
        SET total_budget = EXCLUDED.total_budget,
            total_spent = EXCLUDED.total_spent,
            total_saved = EXCLUDED.total_saved,
            category_breakdown = EXCLUDED.category_breakdown,
            created_at = EXCLUDED.created_at
        """,
        (
            int(user_id),
            str(month_year).strip(),
            float(total_budget),
            float(total_spent),
            float(total_saved),
            json_breakdown,
            now,
        ),
    )
    return True


def get_monthly_budget_history(user_id: int) -> list:
    """Fetch all saved monthly budget reports for the user from Supabase."""
    if not user_id:
        return []
    try:
        rows = query_all(
            """
            SELECT id, user_id, month_year, total_budget, total_spent, total_saved,
                   category_breakdown, created_at
            FROM monthly_budget_history
            WHERE user_id = %s
            ORDER BY month_year DESC, created_at DESC
            """,
            (int(user_id),),
        )
        results = []
        for r in rows:
            cb = r.get("category_breakdown")
            if isinstance(cb, str):
                try:
                    cb = json.loads(cb)
                except Exception:
                    cb = {}
            results.append({
                "id": r["id"],
                "userId": r["user_id"],
                "monthYear": r["month_year"],
                "totalBudget": float(r["total_budget"]),
                "totalSpent": float(r["total_spent"]),
                "totalSaved": float(r["total_saved"]),
                "categoryBreakdown": cb or {},
                "createdAt": str(r.get("created_at") or ""),
            })
        return results
    except Exception:
        return []


def reset_active_monthly_data(user_id: int) -> bool:
    """Clear active personal expenses for the new month."""
    if not user_id:
        return False
    try:
        execute("DELETE FROM personal_expenses WHERE user_id = %s", (int(user_id),))
        return True
    except Exception:
        return False