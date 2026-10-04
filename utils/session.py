"""
utils/session.py
================
Session-state helpers that enforce canonical key names per the UI contract,
and provide session persistence across page reloads using signed HMAC tokens.

Allowed session keys:
    is_authenticated, user_id, username, user_email,
    current_room_id, current_room_name, current_page,
    shopping_mode, selected_bill_id, ocr_results,
    selected_expense_category, selected_expense_start_date,
    selected_expense_end_date
"""

import time
import streamlit as st

try:
    from database.database import get_user_by_id
    from utils.security import (
        create_session_token,
        verify_session_token,
        revoke_session_token,
    )
except ImportError:
    get_user_by_id = None
    create_session_token = None
    verify_session_token = None
    revoke_session_token = None


# ──────────────────────────────────────────────────────
# AUTH PERSISTENCE & BRIDGE
# ──────────────────────────────────────────────────────
def sync_auth_state():
    """
    Bridge and persist auth session state:
    1. If logged_in is already in session_state, ensure canonical keys and armed query params.
    2. If session_state is empty (e.g. browser refreshed/reloaded), recover user from signed query_params['session'].
    """
    # Case 1: Session state is active in memory
    if st.session_state.get("logged_in", False) or st.session_state.get("is_authenticated", False):
        st.session_state["logged_in"] = True
        st.session_state["is_authenticated"] = True

        # Map display name to canonical 'username'
        if "user_name" in st.session_state and not st.session_state.get("username"):
            st.session_state["username"] = st.session_state["user_name"]
        elif "username" in st.session_state and not st.session_state.get("user_name"):
            st.session_state["user_name"] = st.session_state["username"]

        # Ensure user_id exists
        user_id = st.session_state.get("user_id")
        if user_id and create_session_token:
            # Keep query_params armed with signed token for page reloads
            current_token = st.query_params.get("session")
            if not current_token or (verify_session_token and verify_session_token(current_token) != user_id):
                st.query_params["session"] = create_session_token(user_id)
        return

    # Case 2: In-memory session state was cleared by page refresh/reload -> recover from query_params
    token = st.query_params.get("session")
    if token and verify_session_token and get_user_by_id:
        user_id = verify_session_token(token)
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                display_name = user.get("full_name") or user.get("username", "User")
                st.session_state["logged_in"] = True
                st.session_state["is_authenticated"] = True
                st.session_state["user_id"] = user["id"]
                st.session_state["user_email"] = user["email"]
                st.session_state["user_name"] = display_name
                st.session_state["username"] = display_name
                st.session_state["last_activity"] = time.time()
                return

        # Token invalid, expired, or user not found
        st.query_params.clear()

    # Case 3: Not authenticated
    st.session_state["is_authenticated"] = False
    st.session_state["logged_in"] = False


def require_auth():
    """
    Call at the top of every protected page.
    Syncs auth state and redirects to login if not authenticated.
    """
    sync_auth_state()
    if not st.session_state.get("is_authenticated", False):
        st.warning("Please log in to access this page.")
        st.page_link("pages/01_Login.py", label="Go to Login")
        st.stop()


def logout_user():
    """Clear both in-memory session state and persistent session token."""
    token = st.query_params.get("session")
    if token and revoke_session_token:
        revoke_session_token(token)
    st.query_params.clear()
    for key in [
        "logged_in",
        "is_authenticated",
        "user_id",
        "username",
        "user_name",
        "user_email",
        "last_activity",
        "current_room_id",
        "current_room_name",
        "selected_bill_id",
        "ocr_results",
        "shopping_mode",
    ]:
        st.session_state.pop(key, None)


def get_current_user_id() -> int:
    return st.session_state.get("user_id", 1)


def get_username() -> str:
    return st.session_state.get("username", "User")


def set_current_room(room_id: int, room_name: str):
    st.session_state["current_room_id"] = room_id
    st.session_state["current_room_name"] = room_name


def get_current_room_id() -> int | None:
    return st.session_state.get("current_room_id", None)


def get_current_room_name() -> str:
    return st.session_state.get("current_room_name", "")


def clear_current_room():
    st.session_state.pop("current_room_id", None)
    st.session_state.pop("current_room_name", None)
