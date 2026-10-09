import time
import streamlit as st
import sys, os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from style import apply_base_style, top_nav, hide_sidebar, render_dev_mode_banner
from session_manager import check_session_timeout
from database.database import init_db, get_user_by_email, mark_verified, set_otp
from security.authentication import (
    generate_otp,
    otp_expiry_time,
    is_otp_expired,
    send_otp_email,
    smtp_is_configured,
    OTP_RESEND_COOLDOWN_SECONDS,
)

st.set_page_config(
    page_title="Verify Email — GrocEase",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
init_db()
apply_base_style()
hide_sidebar()
top_nav()
check_session_timeout()

email = st.session_state.get("pending_verification_email")

if not email:
    st.warning("Start by creating an account first.")
    if st.button("Go to Create Account"):
        st.switch_page("pages/02_Create_Account.py")
    st.stop()

st.markdown(
    f"""
    <h2 style="text-align:center; margin-bottom:0.2rem;">Verify your email</h2>
    <p class="groc-muted" style="text-align:center; margin-bottom:1.6rem;">
    We've sent a verification code to <b>{email}</b>. Enter the code below to verify your account.
    </p>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([0.2, 3, 0.2])
with mid:
    st.markdown('<div class="groc-card">', unsafe_allow_html=True)

    render_dev_mode_banner()

    if not smtp_is_configured() and st.session_state.get("dev_otp_preview"):
        st.info(
            f"Dev Mode (Live emails disabled): Your verification code is **{st.session_state.dev_otp_preview}**",
            icon="🛠️",
        )

    otp_input = st.text_input(
        "Enter 6-digit code",
        max_chars=6,
        placeholder="______",
        key="otp_input",
    )
    verify_clicked = st.button("Verify Account", type="primary", use_container_width=True)

    st.write(" ")
    now = time.time()
    last_sent = st.session_state.get("otp_last_sent_ts", 0)
    cooldown_remaining = int(OTP_RESEND_COOLDOWN_SECONDS - (now - last_sent))

    resend_col1, resend_col2 = st.columns([2, 1.4])
    with resend_col1:
        st.markdown('<span class="groc-muted">Didn\'t receive the code?</span>', unsafe_allow_html=True)
    with resend_col2:
        st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
        resend_disabled = cooldown_remaining > 0
        resend_label = (
            f"Resend OTP ({cooldown_remaining}s)" if resend_disabled else "Resend OTP"
        )
        resend_clicked = st.button(resend_label, disabled=resend_disabled, key="resend_otp")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

if resend_clicked:
    user = get_user_by_email(email)
    if user:
        new_otp = generate_otp()
        expiry = otp_expiry_time()
        set_otp(email, new_otp, expiry.isoformat())
        send_otp_email(email, new_otp)
        st.session_state.dev_otp_preview = new_otp
        st.session_state.otp_last_sent_ts = time.time()
        st.success("A new code has been sent.")
        st.rerun()

if verify_clicked:
    user = get_user_by_email(email)
    if not user or not user.get("otp_code"):
        st.error("Invalid verification code. Please try again.")
    else:
        try:
            expiry = datetime.fromisoformat(str(user["otp_expires_at"]))
            expired = is_otp_expired(expiry)
        except Exception:
            expired = False

        if expired:
            st.warning("This verification code has expired. Please request a new code.")
        elif otp_input.strip() != str(user["otp_code"]).strip():
            st.error("Invalid verification code. Please try again.")
        else:
            mark_verified(email)
            st.session_state.pop("pending_verification_email", None)
            st.session_state.pop("dev_otp_preview", None)

            # Registration Flow Fix: Do NOT log in automatically.
            # Redirect to Login screen and require manual credential entry.
            st.session_state.registration_success_message = (
                "Account verified successfully! Please log in with your credentials."
            )
            st.switch_page("pages/01_Login.py")