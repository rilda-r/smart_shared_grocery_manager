"""services/shopping_service.py - shopping-trip workflow over the room's grocery list.

Shopping is stateless on the server (no extra tables): ``start_shopping``
returns the pending list, status updates are persisted per item, and
``finish_shopping`` returns a summary. Any room member may mark items
purchased/unavailable while shopping for the room; this is the ONLY write a
non-owner can make to another member's grocery item (status only).
"""

from database.connection import execute, get_cursor, query_all, query_one
from models.grocery_item import GroceryItem
from services.grocery_service import load_grocery_item_for_member
from services.room_service import require_room_member
from utils.helpers import service_call, success_response, utcnow
from utils.validators import validate_grocery_status


def _items(room_id, status=None, cursor=None) -> list:
    sql = "SELECT * FROM grocery_items WHERE room_id = %s"
    params = [room_id]
    if status:
        sql += " AND status = %s"
        params.append(status)
    rows = query_all(sql + " ORDER BY created_at, id", tuple(params), cursor)
    return [GroceryItem.from_row(r).to_dict() for r in rows]


@service_call
def get_pending_grocery_items(user_id, room_id):
    require_room_member(room_id, user_id)
    return success_response(_items(room_id, "pending"))


@service_call
def start_shopping(user_id, room_id):
    require_room_member(room_id, user_id)
    return success_response(
        {
            "room_id": room_id,
            "started_by": user_id,
            "started_at": utcnow(),
            "items": _items(room_id, "pending"),
        },
        "Shopping started.",
    )


@service_call
def update_grocery_item_status(user_id, grocery_item_id, status):
    status = validate_grocery_status(status)
    with get_cursor() as cur:
        item = load_grocery_item_for_member(grocery_item_id, user_id, cur, for_update=True)
        execute(
            "UPDATE grocery_items SET status = %s WHERE id = %s",
            (status, grocery_item_id),
            cur,
        )
        row = query_one("SELECT * FROM grocery_items WHERE id = %s", (item["id"],), cur)
    return success_response(GroceryItem.from_row(row).to_dict(), "Status updated.")


@service_call
def finish_shopping(user_id, room_id):
    require_room_member(room_id, user_id)
    purchased = _items(room_id, "purchased")
    unavailable = _items(room_id, "unavailable")
    pending = _items(room_id, "pending")
    return success_response(
        {
            "room_id": room_id,
            "finished_at": utcnow(),
            "purchased": purchased,
            "unavailable": unavailable,
            "pending": pending,
            "counts": {
                "purchased": len(purchased),
                "unavailable": len(unavailable),
                "pending": len(pending),
            },
        },
        "Shopping finished.",
    )
