import streamlit as st
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from style import apply_base_style, top_nav, hide_sidebar
from session_manager import check_session_timeout
from database.database import (
    init_db,
    create_user,
    get_user_by_email,
    set_otp,
    update_unverified_user,
)
from security.password_hash import hash_password, password_strength
from security.authentication import (
    generate_otp,
    otp_expiry_time,
    is_valid_email,
    send_otp_email,
)

st.set_page_config(
    page_title="Create Account — GrocEase",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
init_db()
apply_base_style()
hide_sidebar()
top_nav()
check_session_timeout()

if "reg_password" not in st.session_state:
    st.session_state.reg_password = ""

st.markdown(
    """
    <h2 style="text-align:center; margin-bottom:0.2rem;">Create your GrocEase account</h2>
    <p class="groc-muted" style="text-align:center; margin-bottom:1.8rem;">
    Start managing your groceries and expenses smarter.
    </p>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([0.1, 3.8, 0.1])
with mid:
    st.markdown('<div class="groc-card">', unsafe_allow_html=True)
    
    full_name = st.text_input("Full Name", placeholder="e.g. Ananya Rao")
    email = st.text_input("Email Address", placeholder="you@example.com")
    st.markdown(
        '<p style="font-size:0.83rem; color:#5C0203; margin-top:-0.4rem; margin-bottom:1rem; font-weight:600;">'
        '⚠️ Email address cannot be changed after account creation.'
        '</p>',
        unsafe_allow_html=True,
    )

    # Standardized Password and Confirm Password fields (redundant dual-eye buttons removed)
    show_passwords = st.checkbox("Show passwords", key="reg_show_passwords")
    pw_type = "default" if show_passwords else "password"

    password = st.text_input(
        "Password",
        type=pw_type,
        placeholder="Create a strong password",
        key="reg_password_input",
    )

    confirm_password = st.text_input(
        "Confirm Password",
        type=pw_type,
        placeholder="Re-enter your password",
        key="reg_confirm_password_input",
    )

    # Live password strength indicator
    if password:
        checks = password_strength(password)
        st.markdown('<p style="font-size:0.95rem; font-weight:700; margin-top:0.8rem; color:#372713;">Password requirements</p>', unsafe_allow_html=True)
        labels = {
            "length": "At least 8 characters",
            "uppercase": "Uppercase letter",
            "lowercase": "Lowercase letter",
            "number": "Number",
            "special": "Special character",
        }
        rows = st.columns(2)
        for i, key in enumerate(labels):
            ok = checks[key]
            icon = "✓" if ok else "✗"
            color = "#4D4828" if ok else "#5C0203"
            with rows[i % 2]:
                st.markdown(
                    f'<div style="color:{color}; font-weight: 600; font-size: 0.88rem; padding: 0.2rem 0;">{icon} {labels[key]}</div>',
                    unsafe_allow_html=True,
                )

    st.write("")
    create_clicked = st.button("Create Account", type="primary", use_container_width=True)

    st.markdown("<p style='text-align:center; margin-top:1rem; font-size:0.92rem; color:#372713; font-weight:500;'>Already have an account?</p>", unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
    st.page_link("pages/01_Login.py", label="Login to your account")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---- ACTIONS LOGIC PROCESSING ----
if create_clicked:
    errors = []
    clean_email = email.strip().lower()
    
    if not full_name.strip():
        errors.append("Please enter your full name.")
    if not email.strip() or not is_valid_email(clean_email):
        errors.append("Please enter a valid email address.")

    if not password:
        errors.append("Please create a password.")
    elif not password_strength(password)["valid"]:
        errors.append("Your password doesn't meet all the requirements above.")
    if password != confirm_password:
        errors.append("Passwords don't match.")
    existing = get_user_by_email(clean_email) if clean_email else None
    if existing and existing.get("is_verified"):
        errors.append("An account with this email already exists. Please log in instead.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        hashed = hash_password(password)
        if existing and not existing.get("is_verified"):
            update_unverified_user(full_name, clean_email, hashed)
            created = True
        else:
            created = create_user(full_name, clean_email, hashed)

        if not created:
            st.error("An account with this email already exists.")
        else:
            otp = generate_otp()
            expiry = otp_expiry_time()
            set_otp(clean_email, otp, expiry.isoformat())
            send_otp_email(clean_email, otp)

            st.session_state.pending_verification_email = clean_email
            st.session_state.dev_otp_preview = otp  
            st.switch_page("pages/03_Verify_Email.py")