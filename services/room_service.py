"""services/room_service.py - room creation, joining, leaving and membership checks."""

from database.connection import DatabaseError, execute, get_cursor, query_all, query_one
from models.room import Room
from services.auth_service import require_user
from utils.helpers import ServiceError, service_call, success_response, utcnow
from utils.security import generate_room_code
from utils.validators import (
    is_valid_room_code_format,
    normalize_room_code,
    validate_id,
    validate_room_name,
)

INVALID_CODE_MESSAGE = "That room code is not valid."


# ---------------------------------------------------------------------------
# Shared authorization helpers (imported by other services)
# ---------------------------------------------------------------------------
def get_member_role(room_id: int, user_id: int, cursor=None):
    row = query_one(
        "SELECT role FROM room_members WHERE room_id = %s AND user_id = %s",
        (room_id, user_id),
        cursor,
    )
    return row["role"] if row else None


def require_room_member(room_id, user_id, cursor=None) -> str:
    """Return the caller's role in ``room_id`` or raise ``not_a_member``."""
    validate_id(room_id, "room id")
    validate_id(user_id, "user id")
    role = get_member_role(room_id, user_id, cursor)
    if role is None:
        raise ServiceError("You are not a member of this room.", "not_a_member")
    return role


def _room_public(room_row: dict, role: str, member_count: int) -> dict:
    data = Room.from_row(room_row).to_dict()
    data["role"] = role
    data["member_count"] = member_count
    return data


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
@service_call
def validate_room_code(secret_code):
    code = normalize_room_code(secret_code)
    if not is_valid_room_code_format(code):
        raise ServiceError(INVALID_CODE_MESSAGE, "invalid_room_code")
    room = query_one("SELECT id, name FROM rooms WHERE secret_code = %s", (code,))
    if room is None:
        raise ServiceError(INVALID_CODE_MESSAGE, "invalid_room_code")
    return success_response({"room_id": room["id"], "name": room["name"]})


@service_call
def create_room(user_id, name):
    name = validate_room_name(name)
    require_user(user_id)
    for _ in range(8):  # collisions are astronomically rare; retry on unique hit
        code = generate_room_code()
        try:
            with get_cursor() as cur:
                now = utcnow()
                room_id = execute(
                    "INSERT INTO rooms (name, secret_code, creator_id, created_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (name, code, user_id, now),
                    cur,
                )
                execute(
                    "INSERT INTO room_members (room_id, user_id, role, joined_at) "
                    "VALUES (%s, %s, 'creator', %s)",
                    (room_id, user_id, now),
                    cur,
                )
                room = query_one("SELECT * FROM rooms WHERE id = %s", (room_id,), cur)
            return success_response(_room_public(room, "creator", 1), "Room created.")
        except DatabaseError as exc:
            if not exc.is_duplicate:
                raise
    raise ServiceError("Could not generate a unique room code. Please retry.", "code_generation_failed")


@service_call
def join_room(user_id, secret_code):
    require_user(user_id)
    code = normalize_room_code(secret_code)
    if not is_valid_room_code_format(code):
        raise ServiceError(INVALID_CODE_MESSAGE, "invalid_room_code")
    try:
        with get_cursor() as cur:
            room = query_one("SELECT * FROM rooms WHERE secret_code = %s", (code,), cur)
            if room is None:
                raise ServiceError(INVALID_CODE_MESSAGE, "invalid_room_code")
            if get_member_role(room["id"], user_id, cur) is not None:
                raise ServiceError("You are already a member of this room.", "duplicate_membership")
            execute(
                "INSERT INTO room_members (room_id, user_id, role, joined_at) "
                "VALUES (%s, %s, 'member', %s)",
                (room["id"], user_id, utcnow()),
                cur,
            )
            count = query_one(
                "SELECT COUNT(*) AS c FROM room_members WHERE room_id = %s", (room["id"],), cur
            )["c"]
    except DatabaseError as exc:  # concurrent double-join hits the primary key
        if exc.is_duplicate:
            raise ServiceError("You are already a member of this room.", "duplicate_membership")
        raise
    return success_response(_room_public(room, "member", count), "Joined room.")


@service_call
def get_user_rooms(user_id):
    require_user(user_id)
    rows = query_all(
        "SELECT r.*, m.role AS member_role, "
        "(SELECT COUNT(*) FROM room_members WHERE room_id = r.id) AS member_count "
        "FROM rooms r JOIN room_members m ON m.room_id = r.id AND m.user_id = %s "
        "ORDER BY r.created_at DESC, r.id DESC",
        (user_id,),
    )
    return success_response([_room_public(r, r["member_role"], r["member_count"]) for r in rows])


@service_call
def get_room_members(user_id, room_id):
    """Members of a room (RoomMember fields plus ``username`` for display)."""
    require_room_member(room_id, user_id)
    rows = query_all(
        "SELECT m.room_id, m.user_id, m.role, m.joined_at, u.username "
        "FROM room_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.room_id = %s ORDER BY m.joined_at, m.user_id",
        (room_id,),
    )
    return success_response(rows)


@service_call
def leave_room(user_id, room_id):
    """Leave safely.

    * Blocked while the user has unsettled payments in the room.
    * Last member leaving deletes the room.
    * Creator leaving hands ownership to the longest-standing member.
    """
    with get_cursor() as cur:
        role = require_room_member(room_id, user_id, cur)
        query_one("SELECT id FROM rooms WHERE id = %s FOR UPDATE", (room_id,), cur)
        outstanding = query_one(
            "SELECT COUNT(*) AS c FROM payments WHERE room_id = %s "
            "AND payment_status <> 'settled' AND (payer_user_id = %s OR payee_user_id = %s)",
            (room_id, user_id, user_id),
            cur,
        )["c"]
        if outstanding:
            raise ServiceError(
                "Settle your outstanding payments before leaving this room.",
                "outstanding_payments",
            )
        others = query_all(
            "SELECT user_id FROM room_members WHERE room_id = %s AND user_id <> %s "
            "ORDER BY joined_at, user_id",
            (room_id, user_id),
            cur,
        )
        if not others:
            execute("DELETE FROM rooms WHERE id = %s", (room_id,), cur)
            return success_response(None, "You left the room. It was empty and has been removed.")

        execute("DELETE FROM grocery_items WHERE room_id = %s AND user_id = %s", (room_id, user_id), cur)
        execute(
            "UPDATE bill_items SET assigned_user_id = NULL WHERE assigned_user_id = %s "
            "AND bill_id IN (SELECT id FROM bills WHERE room_id = %s) "
            "AND bill_id NOT IN (SELECT bill_id FROM payments WHERE room_id = %s)",
            (user_id, room_id, room_id),
            cur,
        )
        execute("DELETE FROM room_members WHERE room_id = %s AND user_id = %s", (room_id, user_id), cur)
        if role == "creator":
            heir = others[0]["user_id"]
            execute("UPDATE rooms SET creator_id = %s WHERE id = %s", (heir, room_id), cur)
            execute(
                "UPDATE room_members SET role = 'creator' WHERE room_id = %s AND user_id = %s",
                (room_id, heir),
                cur,
            )
    return success_response(None, "You left the room.")
