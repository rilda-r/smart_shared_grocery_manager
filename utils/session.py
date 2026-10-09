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
                display_nick = user.get("profile_nickname") or user.get("nickname")
                full_name = user.get("full_name") or user.get("username", "User")
                st.session_state["logged_in"] = True
                st.session_state["is_authenticated"] = True
                st.session_state["user_id"] = user["id"]
                st.session_state["user_email"] = user["email"]
                st.session_state["user_name"] = full_name
                st.session_state["actual_name"] = full_name
                st.session_state["nickname"] = display_nick
                st.session_state["username"] = display_nick or full_name
                st.session_state["last_activity"] = time.time()
                return

        # Token invalid, expired, or user not found
        st.query_params.clear()

    # Case 3: Not authenticated
    st.session_state["is_authenticated"] = False
    st.session_state["logged_in"] = False


def enforce_nickname_onboarding():
    """Prompt the user with a mandatory onboarding screen to choose a nickname on first login."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    nick = st.session_state.get("nickname")
    if not nick:
        from database.database import get_profile, update_nickname
        prof = get_profile(user_id)
        if prof and prof.get("nickname"):
            st.session_state["nickname"] = prof["nickname"]
            st.session_state["username"] = prof["nickname"]
            st.session_state["user_name"] = prof["nickname"]
            st.session_state["actual_name"] = prof.get("actual_name") or prof.get("full_name", "")
            return

        # Mandatory Onboarding Screen
        st.markdown(
            """
            <div style="background:#FFFFFF; border:2px solid #1F4C3D; border-radius:12px;
                        padding:2rem 2.5rem; max-width:560px; margin:2.5rem auto 1.5rem auto;
                        box-shadow:0 10px 32px rgba(31,76,61,0.12); text-align:center;">
                <div style="font-size:3rem; margin-bottom:0.4rem;">👋</div>
                <h2 style="margin-bottom:0.4rem; color:#1F4C3D; font-family:'Fraunces',Georgia,serif;">Choose your Nickname</h2>
                <p style="color:#5B6459; font-size:0.95rem; margin-bottom:1rem; line-height:1.5;">
                    Welcome to GrocEase! Please choose a public <strong>Nickname</strong>.
                    This nickname will be your public displayed name across all rooms, grocery lists, and expense splits.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _, mcol, _ = st.columns([1, 2, 1])
        with mcol:
            with st.form("mandatory_nickname_onboarding_form"):
                new_nick = st.text_input("Your Public Nickname", placeholder="e.g. Alex, ChefSam, Maya")
                st.caption("2–30 characters. You can update this later in your Profile.")
                submitted = st.form_submit_button("Save & Continue", type="primary", use_container_width=True)

                if submitted:
                    cleaned = new_nick.strip()
                    if len(cleaned) < 2 or len(cleaned) > 30:
                        st.error("Nickname must be between 2 and 30 characters.")
                    else:
                        update_nickname(user_id, cleaned)
                        st.session_state["nickname"] = cleaned
                        st.session_state["username"] = cleaned
                        st.session_state["user_name"] = cleaned
                        st.success(f"Welcome, {cleaned}!")
                        st.rerun()

        st.stop()


def require_auth():
    """
    Call at the top of every protected page.
    Syncs auth state, redirects to login if not authenticated, and enforces nickname onboarding.
    """
    sync_auth_state()
    if not st.session_state.get("is_authenticated", False):
        from style import hide_sidebar
        hide_sidebar()
        st.warning("Please log in to access this page.")
        st.page_link("pages/01_Login.py", label="Go to Login")
        st.stop()

    enforce_nickname_onboarding()


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
        "nickname",
        "actual_name",
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
    return st.session_state.get("nickname") or st.session_state.get("username", "User")


def get_actual_name() -> str:
    return st.session_state.get("actual_name") or st.session_state.get("user_name", "")



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
