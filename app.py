"""
app.py – Unified Launch Page with "Cart Drop & Bounce" Splash Animation.
Bounces straight into a high-contrast, beautiful dual-column Login interface.
Fixed the Create Account bottom routing navigation layout mechanics.
"""
import streamlit as st
import time
import sys, os
from dotenv import load_dotenv

load_dotenv()

# Ensure sub-modules can be discovered natively from root context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from style import apply_base_style, top_nav, hide_sidebar, render_dev_mode_banner
from database.database import (
    init_db,
    get_user_by_email,
    record_failed_login,
    reset_failed_login,
    delete_user_account,
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

# Auto-recover session on page reload/navigation
sync_auth_state()
if st.session_state.get("logged_in", False) or st.session_state.get("is_authenticated", False):
    st.session_state.splash_completed = True
    st.switch_page("pages/06_Dashboard.py")


# ----------------- PHASE 1: SPLASH SCREEN SEQUENCE -----------------
if "splash_completed" not in st.session_state:
    st.session_state.splash_completed = False

if not st.session_state.splash_completed:
    st.markdown(
        """
        <style>
            #splash {
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background: #0F766E;
                z-index: 100000;
                display: flex; 
                flex-direction: column;
                align-items: center; 
                justify-content: center;
                overflow: hidden;
            }
            .splash-content { 
                position: relative; 
                text-align: center; 
                color: #FFFFFF; 
                width: 100%;
                max-width: 600px;
                margin: 0 auto;
            }
            .cart { 
                font-size: 5rem; 
                display: inline-block; 
                animation: cartSlide 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; 
                transform: translateX(-200%); 
            }
            @keyframes cartSlide { 
                0% { transform: translateX(-200%); } 
                70% { transform: translateX(10%); } 
                100% { transform: translateX(0%); } 
            }
            .apple { 
                font-size: 2.2rem; 
                position: absolute; 
                top: -80px; 
                left: 50%; 
                transform: translateX(-50%); 
                animation: appleDrop 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) 0.6s forwards; 
                opacity: 0; 
            }
            @keyframes appleDrop { 
                0% { top: -80px; opacity: 0; } 
                50% { top: -5px; opacity: 1; } 
                70% { top: -20px; } 
                100% { top: -12px; opacity: 1; } 
            }
            .brand-text { 
                font-family: 'Fraunces', Georgia, serif; 
                font-size: 3.5rem; 
                font-weight: 800; 
                margin-top: 1.5rem; 
                display: block !important;
                visibility: visible !important;
                transform: scale(0); 
                animation: textBounce 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) 1.1s forwards; 
                color: #FFFFFF !important; 
            }
            @keyframes textBounce { 
                0% { transform: scale(0); } 
                60% { transform: scale(1.1); } 
                100% { transform: scale(1); } 
            }
            .tagline { 
                font-family: 'Plus Jakarta Sans', sans-serif; 
                font-size: 1.1rem; 
                opacity: 0; 
                margin-top: 0.5rem;
                animation: fadeUp 0.6s ease 1.3s forwards; 
                color: #DCEBE7 !important; 
            }
            @keyframes fadeUp { 
                0% { opacity: 0; transform: translateY(10px); } 
                100% { opacity: 0.9; transform: translateY(0); } 
            }
        </style>
        <div id="splash">
            <div class="splash-content">
                <div style="position: relative; display: inline-block; width: 100px; height: 100px;">
                    <span class="cart">🛒</span>
                    <span class="apple">🍎</span>
                </div>
                <h1 class="brand-text">GrocEase</h1>
                <div class="tagline">Shop together. Split smarter.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(0.4)
    st.session_state.splash_completed = True
    st.rerun()

# ----------------- PHASE 2: AUTHENTICATED USER INTERFACE -----------------
if st.session_state.get("logged_in", False):
    # Bridge legacy auth keys → canonical contract keys
    if "username" not in st.session_state and "user_name" in st.session_state:
        st.session_state["username"] = st.session_state["user_name"]
    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = True
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = 1  # Mock user_id — replaced by backend
    # Redirect to Dashboard
    st.switch_page("pages/06_Dashboard.py")

# ----------------- PHASE 3: LIVE MAIN LOGIN LAYOUT -----------------
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
    if "registration_success_message" in st.session_state:
        st.success(f"✅ {st.session_state.pop('registration_success_message')}")

    with st.container(border=True):
        render_dev_mode_banner()
        st.markdown("### Login", unsafe_allow_html=True)
        st.write("")

        email = st.text_input("Email Address", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        st.page_link("pages/04_Forgot_Password.py", label="Forgot Password?")

        st.write("")
        login_clicked = st.button("Login", type="primary", use_container_width=True)

        # ---- NATIVE STREAMLIT NAVIGATION ROW (ALIGNED ON SAME BASELINE) ----
        st.write(" ")
        footer_col1, footer_col2 = st.columns([1, 1], vertical_alignment="center")
        with footer_col1:
            st.markdown('<p style="text-align:right; margin:0; font-size:0.95rem; color:#10272A; font-weight:500;">New here?</p>', unsafe_allow_html=True)
        with footer_col2:
            st.page_link("pages/02_Create_Account.py", label="Create Account")

# ----------------- PHASE 4: EXECUTION BUSINESS LOGIC -----------------
if login_clicked:
    if not email.strip() or not password:
        st.error("Please enter both your email and password.")
    else:
        user = get_user_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            if user:
                record_failed_login(email)
            st.error("Incorrect email or password.")
        elif not user["is_verified"]:
            st.warning("This account hasn't been verified yet.")
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
