"""
utils/session.py
================
Session-state helpers that enforce canonical key names per the UI contract.

Allowed session keys:
    is_authenticated, user_id, username, user_email,
    current_room_id, current_room_name, current_page,
    shopping_mode, selected_bill_id, ocr_results,
    selected_expense_category, selected_expense_start_date,
    selected_expense_end_date
"""

import streamlit as st


# ──────────────────────────────────────────────────────
# AUTH BRIDGE
# The existing auth layer uses "logged_in" / "user_name" / "user_email".
# We bridge those to the canonical contract keys on first access.
# ──────────────────────────────────────────────────────
def sync_auth_state():
    """
    Bridge the existing auth session keys (logged_in, user_name, user_email)
    to the canonical UI-contract keys (is_authenticated, username, user_email).
    """
    if st.session_state.get("logged_in", False):
        if not st.session_state.get("is_authenticated"):
            st.session_state["is_authenticated"] = True
        # user_name set by login page — map to canonical 'username'
        if "user_name" in st.session_state and "username" not in st.session_state:
            st.session_state["username"] = st.session_state["user_name"]
        # user_email is already the correct key, leave it
        # Seed a mock user_id if not set (backend will provide real value)
        if "user_id" not in st.session_state:
            st.session_state["user_id"] = 1  # default mock user
    else:
        st.session_state["is_authenticated"] = False


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
