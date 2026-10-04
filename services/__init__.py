"""
GrocEase backend services package.
"""

from services.auth_service import (
    authenticate_user,
    logout_user,
    register_user,
    validate_login_attempts,
    validate_session,
)
from services.grocery_service import (
    add_grocery_item,
    delete_grocery_item,
    get_grocery_items,
    update_grocery_item,
)
from services.room_service import (
    create_room,
    get_room_members,
    get_user_rooms,
    join_room,
    leave_room,
    validate_room_code,
)

__all__ = [
    # Auth
    "register_user",
    "authenticate_user",
    "validate_login_attempts",
    "validate_session",
    "logout_user",
    # Room
    "create_room",
    "join_room",
    "get_user_rooms",
    "get_room_members",
    "leave_room",
    "validate_room_code",
    # Grocery
    "add_grocery_item",
    "get_grocery_items",
    "update_grocery_item",
    "delete_grocery_item",
]
