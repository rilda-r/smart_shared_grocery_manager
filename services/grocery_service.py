"""services/grocery_service.py - shared grocery list with owner-only modification."""

from database.connection import execute, get_cursor, query_all, query_one
from models.grocery_item import GroceryItem
from services.auth_service import require_user
from services.room_service import require_room_member
from utils.helpers import UNSET, ServiceError, service_call, success_response
from utils.validators import (
    validate_grocery_quantity,
    validate_grocery_status,
    validate_id,
    validate_item_name,
)


def load_grocery_item_for_member(grocery_item_id, user_id, cursor, for_update=False) -> dict:
    """Fetch an item the caller may SEE (room member). Non-members get ``not_found``."""
    validate_id(grocery_item_id, "grocery item id")
    validate_id(user_id, "user id")
    sql = "SELECT * FROM grocery_items WHERE id = %s" + (" FOR UPDATE" if for_update else "")
    item = query_one(sql, (grocery_item_id,), cursor)
    if item is None:
        raise ServiceError("Grocery item not found.", "not_found")
    member = query_one(
        "SELECT 1 AS ok FROM room_members WHERE room_id = %s AND user_id = %s",
        (item["room_id"], user_id),
        cursor,
    )
    if member is None:
        raise ServiceError("Grocery item not found.", "not_found")
    return item


def _public(row: dict) -> dict:
    return GroceryItem.from_row(row).to_dict()


@service_call
def add_grocery_item(user_id, room_id, item_name, quantity=1, status="pending"):
    item_name = validate_item_name(item_name)
    quantity = validate_grocery_quantity(quantity)
    status = validate_grocery_status(status)
    with get_cursor() as cur:
        require_room_member(room_id, user_id, cur)
        item_id = execute(
            "INSERT INTO grocery_items (room_id, user_id, item_name, quantity, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (room_id, user_id, item_name, quantity, status),
            cur,
        )
        row = query_one("SELECT * FROM grocery_items WHERE id = %s", (item_id,), cur)
    return success_response(_public(row), "Item added.")


@service_call
def get_grocery_items(user_id, room_id, status=None):
    """All items in the room (any member may view)."""
    require_room_member(room_id, user_id)
    sql = "SELECT * FROM grocery_items WHERE room_id = %s"
    params = [room_id]
    if status is not None:
        params.append(validate_grocery_status(status))
        sql += " AND status = %s"
    rows = query_all(sql + " ORDER BY created_at, id", tuple(params))
    return success_response([_public(r) for r in rows])


@service_call
def update_grocery_item(user_id, grocery_item_id, item_name=UNSET, quantity=UNSET, status=UNSET):
    """Owner-only edit of name / quantity / status."""
    changes = {}
    if item_name is not UNSET:
        changes["item_name"] = validate_item_name(item_name)
    if quantity is not UNSET:
        changes["quantity"] = validate_grocery_quantity(quantity)
    if status is not UNSET:
        changes["status"] = validate_grocery_status(status)
    if not changes:
        raise ServiceError("Nothing to update.", "invalid_input")
    with get_cursor() as cur:
        item = load_grocery_item_for_member(grocery_item_id, user_id, cur, for_update=True)
        if item["user_id"] != user_id:
            raise ServiceError("You can only modify your own grocery items.", "not_authorized")
        assignments = ", ".join(f"{col} = %s" for col in changes)  # column names are constants
        execute(
            f"UPDATE grocery_items SET {assignments} WHERE id = %s",
            (*changes.values(), grocery_item_id),
            cur,
        )
        row = query_one("SELECT * FROM grocery_items WHERE id = %s", (grocery_item_id,), cur)
    return success_response(_public(row), "Item updated.")


@service_call
def delete_grocery_item(user_id, grocery_item_id):
    """Owner-only delete."""
    with get_cursor() as cur:
        item = load_grocery_item_for_member(grocery_item_id, user_id, cur, for_update=True)
        if item["user_id"] != user_id:
            raise ServiceError("You can only delete your own grocery items.", "not_authorized")
        execute("DELETE FROM grocery_items WHERE id = %s", (grocery_item_id,), cur)
    return success_response({"id": grocery_item_id}, "Item deleted.")
