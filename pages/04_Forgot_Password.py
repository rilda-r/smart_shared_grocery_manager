import time
import streamlit as st
import sys, os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from style import apply_base_style, top_nav, hide_sidebar
from session_manager import check_session_timeout
from database.database import (
    init_db, get_user_by_email, set_otp, clear_otp, update_password,
)
from security.password_hash import hash_password, password_strength
from security.authentication import (
    generate_otp, otp_expiry_time, is_otp_expired,
    send_otp_email, smtp_is_configured, is_valid_email,
    OTP_RESEND_COOLDOWN_SECONDS,
)

st.set_page_config(
    page_title="Reset Password — GrocEase",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
init_db()
apply_base_style()
hide_sidebar()
top_nav()
check_session_timeout()


# Initialize flow state keys safely
if "fp_step" not in st.session_state:
    st.session_state.fp_step = "email"
if "fp_email" not in st.session_state:
    st.session_state.fp_email = ""
if "fp_dev_otp" not in st.session_state:
    st.session_state.fp_dev_otp = None
if "fp_last_sent_ts" not in st.session_state:
    st.session_state.fp_last_sent_ts = 0

st.markdown(
    """
    <h2 style="text-align:center; margin-bottom:0.2rem;">Reset your password</h2>
    <p class="groc-muted" style="text-align:center; margin-bottom:1.6rem;">
    Verify your identity with an OTP, then set a new password.
    </p>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([0.2, 3, 0.2])
with mid:
    st.markdown('<div class="groc-card">', unsafe_allow_html=True)

    # ---- STEP 1: EMAIL ----
    if st.session_state.fp_step == "email":
        st.markdown("#### Step 1 · Enter your email")
        email_input = st.text_input("Email Address", placeholder="you@example.com")
        
        if st.button("Send OTP", type="primary", use_container_width=True):
            clean = email_input.strip().lower()
            if not is_valid_email(clean):
                st.error("Please enter a valid email address.")
            else:
                user = get_user_by_email(clean)
                if not user:
                    st.error("No account found with this email. Please register first.")
                else:
                    # If SMTP isn't configured, default to fallback OTP '123456'
                    otp = generate_otp() if smtp_is_configured() else "123456"
                    expiry = otp_expiry_time()
                    set_otp(clean, otp, expiry.isoformat())
                    
                    if smtp_is_configured():
                        send_otp_email(clean, otp)

                    st.session_state.fp_email = clean
                    st.session_state.fp_dev_otp = otp
                    st.session_state.fp_last_sent_ts = time.time()
                    st.session_state.fp_step = "otp"
                    st.rerun()

        st.markdown('<div class="forgot-link" style="margin-top:1rem;">', unsafe_allow_html=True)
        st.page_link("pages/01_Login.py", label="← Back to Login")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- STEP 2: OTP ----
    elif st.session_state.fp_step == "otp":
        st.markdown("#### Step 2 · Enter the OTP")
        st.markdown(f'<p class="groc-muted" style="font-size:0.92rem;">Sent to <b>{st.session_state.fp_email}</b>.</p>', unsafe_allow_html=True)

        if not smtp_is_configured():
            st.info(f"🛠️ Dev Mode Active (No SMTP): Use code **{st.session_state.fp_dev_otp}**", icon="ℹ️")

        otp_input = st.text_input("Enter 6-digit code", max_chars=6, placeholder="______", value=st.session_state.fp_dev_otp if not smtp_is_configured() else "")

        now = time.time()
        cooldown = int(OTP_RESEND_COOLDOWN_SECONDS - (now - st.session_state.fp_last_sent_ts))
        rc1, rc2 = st.columns([2, 1.4])
        with rc1:
            st.markdown('<span class="groc-muted">Didn\'t receive it?</span>', unsafe_allow_html=True)
        with rc2:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button(f"Resend ({cooldown}s)" if cooldown > 0 else "Resend OTP",
                         disabled=cooldown > 0, key="fp_resend"):
                new_otp = generate_otp() if smtp_is_configured() else "123456"
                set_otp(st.session_state.fp_email, new_otp, otp_expiry_time().isoformat())
                if smtp_is_configured():
                    send_otp_email(st.session_state.fp_email, new_otp)
                st.session_state.fp_dev_otp = new_otp
                st.session_state.fp_last_sent_ts = time.time()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        if st.button("Verify OTP", type="primary", use_container_width=True):
            user = get_user_by_email(st.session_state.fp_email)
            if not user or not user.get("otp_code"):
                st.error("Invalid verification code.")
            else:
                expiry = datetime.fromisoformat(user["otp_expires_at"])
                if is_otp_expired(expiry):
                    st.warning("Code expired. Request a new one.")
                elif otp_input.strip() != user["otp_code"]:
                    st.error("Invalid verification code.")
                else:
                    st.session_state.fp_step = "reset"
                    st.rerun()

        # Dev bypass option
        if not smtp_is_configured():
            st.markdown("---")
            if st.button("🛠️ Skip OTP Verification (Dev Mode)", use_container_width=True):
                st.session_state.fp_step = "reset"
                st.rerun()

    # ---- STEP 3: NEW PASSWORD ----
    elif st.session_state.fp_step == "reset":
        st.markdown("#### Step 3 · Set a new password")

        show_pw = st.session_state.get("fp_show_pw", False)
        pw_col, pw_toggle = st.columns([5, 1], gap="small")
        with pw_col:
            new_pw = st.text_input("New Password",
                                   type="default" if show_pw else "password",
                                   placeholder="Create a strong password")
        with pw_toggle:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("👁️" if not show_pw else "🙈", key="fp_toggle_pw"):
                st.session_state.fp_show_pw = not show_pw
                st.rerun()

        confirm_pw = st.text_input("Confirm New Password", type="password",
                                   placeholder="Re-enter your new password")

        if new_pw:
            checks = password_strength(new_pw)
            labels = {"length": "At least 8 characters", "uppercase": "Uppercase letter",
                      "lowercase": "Lowercase letter", "number": "Number",
                      "special": "Special character"}
            st.markdown('<p style="font-size:0.95rem; font-weight:600; margin-top:0.6rem;">Password requirements</p>', unsafe_allow_html=True)
            cols = st.columns(2)
            for i, key in enumerate(labels):
                ok = checks[key]
                icon = "✓" if ok else "✗"
                color = "#1F4C3D" if ok else "#9C4B3E"
                with cols[i % 2]:
                    st.markdown(f'<div style="color:{color}; font-weight:500; font-size:0.88rem; padding:0.15rem 0;">{icon} {labels[key]}</div>', unsafe_allow_html=True)

        if st.button("Update Password", type="primary", use_container_width=True):
            errors = []
            if not new_pw:
                errors.append("Enter a new password.")
            elif not password_strength(new_pw)["valid"]:
                errors.append("Password doesn't meet requirements.")
            if new_pw != confirm_pw:
                errors.append("Passwords don't match.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                hashed = hash_password(new_pw)
                update_password(st.session_state.fp_email, hashed)
                clear_otp(st.session_state.fp_email)
                st.session_state.fp_step = "done"
                st.rerun()

    # ---- STEP 4: SUCCESS ----
    elif st.session_state.fp_step == "done":
        st.success("✅ Password updated successfully!")
        for k in ["fp_email", "fp_dev_otp", "fp_last_sent_ts"]:
            st.session_state.pop(k, None)
        st.session_state.fp_step = "email"
        if st.button("Go to Login", type="primary", use_container_width=True):
            st.switch_page("pages/01_Login.py")

    st.markdown("</div>", unsafe_allow_html=True)