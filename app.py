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

from style import apply_base_style, top_nav
from database.database import (
    init_db,
    get_user_by_email,
    record_failed_login,
    reset_failed_login,
    delete_user_account,
)
from security.password_hash import verify_password

st.set_page_config(
    page_title="Login — GrocEase",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()
apply_base_style()

# Hide Streamlit's default multipage sidebar navigation panel
st.markdown(
    "<style>[data-testid='stSidebarNav'] {display: none;}</style>",
    unsafe_allow_html=True,
)

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
                background: #1F4C3D;
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
                color: #F6F2E9; 
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
                font-weight: 700; 
                margin-top: 1.5rem; 
                display: block !important;
                visibility: visible !important;
                transform: scale(0); 
                animation: textBounce 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) 1.1s forwards; 
                color: #F6F2E9 !important; 
            }
            @keyframes textBounce { 
                0% { transform: scale(0); }
                60% { transform: scale(1.1); } 
                100% { transform: scale(1); } 
            }
            .tagline { 
                font-family: 'Inter', sans-serif; 
                font-size: 1.1rem; 
                opacity: 0; 
                margin-top: 0.5rem;
                animation: fadeUp 0.6s ease 1.3s forwards; 
                color: #E7EFE6 !important; 
            }
            @keyframes fadeUp { 
                0% { opacity: 0; transform: translateY(10px); } 
                100% { opacity: 0.8; transform: translateY(0); } 
            }
        </style>
        <div id="splash">
            <div class="splash-content">
                <div style="position: relative; display: inline-block; width: 100px; height: 100px;">
                    <span class="cart">🛒</span>
                    <span class="apple">🍏</span>
                </div>
                <h1 class="brand-text">GrocEase</h1>
                <div class="tagline">Shop together. Split smarter.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(2.5)
    st.session_state.splash_completed = True
    st.rerun()

# ----------------- PHASE 2: AUTHENTICATED USER INTERFACE -----------------
if st.session_state.get("logged_in", False):
    top_nav()
    header_left, header_right = st.columns([4, 1.2])
    
    with header_left:
        st.success(f"✓ Welcome back, {st.session_state.user_name}!")
        st.info("💡 Dashboard is initialized — Login sequence verified successfully.")
        
    with header_right:
        st.markdown('<div class="top-right-dock groc-danger">', unsafe_allow_html=True)
        if st.button("🚨 Delete Account", key="top_delete_account"):
            delete_user_account(st.session_state.user_email)
            st.session_state.logged_in = False
            st.session_state.pop("user_email", None)
            st.session_state.pop("user_name", None)
            st.success("Your account has been permanently deleted.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Dashboard Panel Grids
    st.markdown("<br><br>", unsafe_allow_html=True)
    panel_col1, panel_col2 = st.columns(2, gap="medium")
    with panel_col1:
        st.markdown(
            """
            <div class="groc-panel">
                <div class="groc-feature-icon">🧾</div>
                <h4 style="margin-top:0.5rem;">Recent group activity</h4>
                <p class="groc-muted" style="font-size:0.9rem;">No active groups shared yet. Create a room to start tracking shared lists.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with panel_col2:
        st.markdown(
            """
            <div class="groc-panel">
                <div class="groc-feature-icon">📊</div>
                <h4 style="margin-top:0.5rem;">Personal spend tracker</h4>
                <p class="groc-muted" style="font-size:0.9rem;">Your monthly grocery expense tracking graphs will populate here natively.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.stop()

# ----------------- PHASE 3: LIVE MAIN LOGIN LAYOUT -----------------
top_nav()

left, right = st.columns([1, 1], gap="large")

with left:
    st.write("")
    st.write("")
    st.markdown(
        """
        <h1 style="font-size:2.8rem; margin-bottom: 0.5rem;">Welcome back</h1>
        <p class="groc-muted" style="font-size:1.15rem;">Let's get your groceries sorted.</p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:2.8rem; margin-top:1.5rem;">🛒 🥦 🥛 🍎</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown('<div class="groc-card">', unsafe_allow_html=True)
    st.markdown("### Login", unsafe_allow_html=True)
    st.write("")

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

    st.markdown(
        '<p style="text-align:right; margin-top:-0.4rem;"><a href="#" style="color:#A97A1F; font-weight:500; font-size:0.9rem;">Forgot Password?</a></p>',
        unsafe_allow_html=True,
    )

    st.write("")
    login_clicked = st.button("Login", type="primary", use_container_width=True)

    # ---- NATIVE STREAMLIT NAVIGATION ROW ----
    st.write(" ")
    left_msg_col, right_link_col = st.columns([1.1, 2])
    with left_msg_col:
        st.markdown('<p style="text-align:right; margin-top:0.35rem; font-size:0.95rem; color:#20261F;">New here?</p>', unsafe_allow_html=True)
    with right_link_col:
        st.page_link("pages/02_Create_Account.py", label="Create Account")

    st.markdown("</div>", unsafe_allow_html=True)

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
            if st.button("Verify now"):
                st.switch_page("pages/03_Verify_Email.py")
        else:
            reset_failed_login(email)
            st.session_state.logged_in = True
            st.session_state.user_email = user["email"]
            st.session_state.user_name = user["full_name"]
            st.rerun()
