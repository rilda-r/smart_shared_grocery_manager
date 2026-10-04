import streamlit as st
import sys, os, time
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from style import apply_base_style, top_nav
from session_manager import check_session_timeout
from database.database import (
    init_db, get_user_by_email, record_failed_login, reset_failed_login,
    delete_user_account, lock_account, unlock_account,
)
from security.password_hash import verify_password
from utils.session import sync_auth_state
from utils.security import create_session_token

st.set_page_config(page_title="Login — GrocEase", page_icon="🛒", layout="wide")
init_db()
apply_base_style()
top_nav()

# Run active session timeout check
check_session_timeout()

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_MINUTES = 10

# ============================================================
# LOGGED-IN VIEW — REDIRECT TO DASHBOARD
# ============================================================
sync_auth_state()
if st.session_state.get("logged_in", False) or st.session_state.get("is_authenticated", False):
    st.switch_page("pages/06_Dashboard.py")

# ============================================================
# LOGIN FORM
# ============================================================
left, right = st.columns([1, 1], gap="large")

with left:
    st.write("")
    st.write("")
    st.markdown(
        """
        <h1 style="font-size:2.3rem;">Welcome back</h1>
        <p class="groc-muted" style="font-size:1.05rem;">Let's get your groceries sorted.</p>
        """,
        unsafe_allow_html=True,
    )

with right:
    with st.container(key="login_card"):
        st.markdown("#### Login")

        email = st.text_input("Email Address", placeholder="you@example.com")

        show_pw = st.session_state.get("login_show_pw", False)
        pw_col, pw_toggle = st.columns([5, 1], gap="small")
        with pw_col:
            password = st.text_input(
                "Password",
                type="default" if show_pw else "password",
                placeholder="Enter your password",
            )
        with pw_toggle:
            st.write("")
            st.write("")
            if st.button("👁️" if not show_pw else "🙈", key="login_toggle_pw"):
                st.session_state.login_show_pw = not show_pw
                st.rerun()

        # --- Forgot Password Link (right aligned) ---
        with st.container(key="forgot_link_wrap"):
            st.page_link("pages/04_Forgot_Password.py", label="Forgot Password?")

        login_clicked = st.button("Login", type="primary", use_container_width=True)

        st.markdown(
            "<p style='text-align:center; margin-top:1rem; font-size:0.9rem; color:#20261F; margin-bottom:0.2rem;'>New here?</p>",
            unsafe_allow_html=True,
        )
        with st.container(key="create_account_link_wrap"):
            st.page_link("pages/02_Create_Account.py", label="Create Account")

# ============================================================
# LOGIN LOGIC
# ============================================================
if login_clicked:
    if not email.strip() or not password:
        st.error("Please enter both your email and password.")
    else:
        user = get_user_by_email(email)

        # Lockout check
        if user and user.get("locked_until"):
            try:
                locked_until = datetime.fromisoformat(user["locked_until"])
            except (ValueError, TypeError):
                locked_until = None
            if locked_until and datetime.utcnow() < locked_until:
                remaining = locked_until - datetime.utcnow()
                mins = int(remaining.total_seconds() // 60) + 1
                st.error(f"🔒 Account locked. Try again in **{mins} min**.")
                st.stop()
            else:
                unlock_account(email)
                user = get_user_by_email(email)

        # Credentials check
        if not user or not verify_password(password, user["password_hash"]):
            if user:
                record_failed_login(email)
                refreshed = get_user_by_email(email)
                attempts = refreshed.get("failed_login_attempts", 0)
                if attempts >= MAX_FAILED_ATTEMPTS:
                    lock_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                    lock_account(email, lock_until.isoformat())
                    st.error(f"🔒 Too many failed attempts. Locked for **{LOCKOUT_MINUTES} minutes**.")
                else:
                    attempts_left = MAX_FAILED_ATTEMPTS - attempts
                    st.error(f"Incorrect email or password. **{attempts_left}** attempt(s) left.")
            else:
                st.error("Incorrect email or password.")

        elif not user["is_verified"]:
            st.warning("Account not verified yet.")
            st.session_state.pending_verification_email = email.strip().lower()
            if st.button("Verify now"):
                st.switch_page("pages/03_Verify_Email.py")

        else:
            reset_failed_login(email)
            st.session_state.logged_in = True
            st.session_state.is_authenticated = True
            st.session_state.user_id = user["id"]
            st.session_state.user_email = user["email"]
            st.session_state.user_name = user["full_name"]
            st.session_state.username = user["full_name"]
            st.session_state.last_activity = time.time()

            token = create_session_token(user["id"])
            st.query_params["session"] = token
            st.switch_page("pages/06_Dashboard.py")