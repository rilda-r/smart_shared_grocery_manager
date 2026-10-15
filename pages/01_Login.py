import streamlit as st
import sys, os, time
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from style import apply_base_style, top_nav, hide_sidebar, render_dev_mode_banner
from session_manager import check_session_timeout
from database.database import (
    init_db, get_user_by_email, record_failed_login, reset_failed_login,
    delete_user_account, lock_account, unlock_account,
)
from security.password_hash import verify_password
from utils.session import sync_auth_state
from utils.security import create_session_token

st.set_page_config(
    page_title="Login — GrocEase",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_db()
apply_base_style()
hide_sidebar()

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
    st.markdown(
        """
        <div style="padding:0.2rem 0 1.5rem 0; text-align:left;">
            <div class="groc-logo" style="font-size:2.2rem; margin-bottom:0.1rem;">🛒 GrocEase</div>
            <div class="groc-tagline" style="margin-bottom:2.2rem;">Shop together. Split smarter.</div>
            <h1 style="font-size:2.8rem; margin:0 0 0.5rem 0; line-height:1.15;">Welcome back</h1>
            <p class="groc-muted" style="font-size:1.15rem; margin:0 0 1.5rem 0;">Let's get your groceries sorted.</p>
            <div style="font-size:2.8rem;">🛒 🥦 🥛 🍎</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    # Notification from registration / verification
    if "registration_success_message" in st.session_state:
        st.success(f"✅ {st.session_state.pop('registration_success_message')}")

    with st.container(border=True):
        render_dev_mode_banner()

        st.markdown("#### Login")

        email = st.text_input("Email Address", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        # --- Forgot Password Link (right aligned) ---
        with st.container(key="forgot_link_wrap"):
            st.page_link("pages/04_Forgot_Password.py", label="Forgot Password?")

        login_clicked = st.button("Login", type="primary", use_container_width=True)

        # ---- NATIVE STREAMLIT NAVIGATION ROW (ALIGNED ON SAME BASELINE) ----
        st.write(" ")
        footer_col1, footer_col2 = st.columns([1, 1], vertical_alignment="center")
        with footer_col1:
            st.markdown('<p style="text-align:right; margin:0; font-size:0.95rem; color:#2A1D16; font-weight:500;">New here?</p>', unsafe_allow_html=True)
        with footer_col2:
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
                locked_until = datetime.fromisoformat(str(user["locked_until"]))
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
            st.page_link("pages/03_Verify_Email.py", label="👉 Click here to verify your account")

        else:
            reset_failed_login(email)
            st.session_state.logged_in = True
            st.session_state.is_authenticated = True
            st.session_state.user_id = user["id"]
            st.session_state.user_email = user["email"]
            display_nick = user.get("profile_nickname") or user.get("nickname")
            full_name = user.get("full_name") or user.get("username", "User")
            st.session_state.user_name = full_name
            st.session_state.actual_name = full_name
            st.session_state.nickname = display_nick
            st.session_state.username = display_nick or full_name
            st.session_state.last_activity = time.time()

            token = create_session_token(user["id"])
            st.query_params["session"] = token
            st.switch_page("pages/06_Dashboard.py")