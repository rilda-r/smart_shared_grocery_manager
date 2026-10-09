"""
app.py – Unified Launch Page with "Text Zoom Parallax" Entrance Splash Animation.
Transitions into a sleek, rounded-rectangle geometric authentication interface.
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


# ----------------- PHASE 1: PARALLAX TEXT ZOOM ENTRY SPLASH -----------------
if "splash_completed" not in st.session_state:
    st.session_state.splash_completed = False

if not st.session_state.splash_completed:
    st.markdown(
        """
        <style>
            #parallax-splash {
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background: linear-gradient(135deg, #372713 0%, #251a0d 100%);
                z-index: 100000;
                display: flex; 
                align-items: center; 
                justify-content: center;
                overflow: hidden;
                perspective: 10px;
            }
            .background-blobs {
                position: absolute;
                width: 100%; height: 100%;
                top: 0; left: 0;
                z-index: 1;
            }
            .blob {
                position: absolute;
                border-radius: 50%;
                filter: blur(80px);
                opacity: 0.25;
                animation: drift 8s ease-in-out infinite alternate;
            }
            .blob-rose {
                width: 400px; height: 400px;
                background: #A99670;
                top: -10%; left: -10%;
            }
            .blob-sage {
                width: 500px; height: 500px;
                background: #4D4828;
                bottom: -15%; right: -10%;
                animation-delay: -4s;
            }
            @keyframes drift {
                0% { transform: translateY(0px) scale(1); }
                100% { transform: translateY(40px) scale(1.1); }
            }
            .ui-fragments {
                position: absolute;
                width: 100%; height: 100%;
                z-index: 2;
                pointer-events: none;
            }
            .fragment {
                position: absolute;
                font-size: 2.5rem;
                opacity: 0;
                animation: fragmentFloat 2.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
            }
            .frag-1 { top: 20%; left: 15%; animation-delay: 0.2s; }
            .frag-2 { top: 70%; left: 25%; animation-delay: 0.4s; }
            .frag-3 { top: 15%; right: 20%; animation-delay: 0.3s; }
            .frag-4 { top: 65%; right: 15%; animation-delay: 0.5s; }
            @keyframes fragmentFloat {
                0% { transform: translateZ(-20px) translateY(50px) scale(0.5); opacity: 0; }
                50% { opacity: 0.6; }
                100% { transform: translateZ(5px) translateY(-80px) scale(1.2); opacity: 0; }
            }
            .zoom-container {
                z-index: 3;
                text-align: center;
                transform-style: preserve-3d;
            }
            .brand-zoom { 
                font-family: 'Fraunces', Georgia, serif; 
                font-size: 5.5rem; 
                font-weight: 800; 
                color: #D9C4B1 !important;
                letter-spacing: -1px;
                transform: scale(0.3);
                opacity: 0;
                animation: textZoomIn 2.6s cubic-bezier(0.7, 0, 0.3, 1) forwards;
            }
            @keyframes textZoomIn { 
                0% { transform: scale(0.3) translateZ(-10px); opacity: 0; filter: blur(5px); }
                20% { opacity: 1; filter: blur(0px); }
                75% { transform: scale(1.5) translateZ(2px); opacity: 0.9; }
                100% { transform: scale(8) translateZ(8px); opacity: 0; filter: blur(10px); } 
            }
        </style>
        <div id="parallax-splash">
            <div class="background-blobs">
                <div class="blob blob-rose"></div>
                <div class="blob blob-sage"></div>
            </div>
            <div class="ui-fragments">
                <span class="fragment frag-1">🥛</span>
                <span class="fragment frag-2">🥦</span>
                <span class="fragment frag-3">🍎</span>
                <span class="fragment frag-4">🔒</span>
            </div>
            <div class="zoom-container">
                <h1 class="brand-zoom">GrocEase</h1>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(2.4)
    st.session_state.splash_completed = True
    st.rerun()

# ----------------- PHASE 2: AUTHENTICATED REDIRECTS -----------------
if st.session_state.get("logged_in", False):
    if "username" not in st.session_state and "user_name" in st.session_state:
        st.session_state["username"] = st.session_state["user_name"]
    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = True
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = 1
    st.switch_page("pages/06_Dashboard.py")

# ----------------- PHASE 3: GEOMETRIC AUTH LAYOUT -----------------
# Inject global rounded rectangle geometry rules overrides globally
st.markdown(
    """
    <style>
        /* Force heavily rounded corners across input components */
        .stTextInput div[data-baseweb="input"] {
            border-radius: 20px !important;
            border: 1px solid #E2E8F0 !important;
        }
        button[kind="primary"], button[kind="secondary"] {
            border-radius: 20px !important;
            padding: 0.5rem 1.5rem !important;
            font-weight: 600 !important;
        }
        div[data-testid="stForm"] {
            border-radius: 24px !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
            background-color: #FFFFFF !important;
            padding: 2.5rem !important;
        }
        .auth-header-card {
            background-color: #FFFFFF;
            border-radius: 24px;
            padding: 2rem;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Render Horizontal Upper Action Panel Structure
top_nav()

# Main Container using balanced structural split layout grids
left_layout, right_form = st.columns([1, 1], gap="large")

with left_layout:
    st.markdown(
        """
        <div class="auth-header-card">
            <h1 style="font-family:'Fraunces',serif; font-size: 2.6rem; color: #372713; margin-bottom: 0.5rem;">Welcome Back</h1>
            <p style="color: #64748B; font-size: 1.1rem; margin-bottom: 1.5rem;">Access your household's collaborative grocery boards instantly.</p>
            <div style="font-size: 2.2rem; display: flex; gap: 0.75rem;">
                <span>🛒</span><span>🥑</span><span>🥛</span><span>🏷️</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_form:
    if "registration_success_message" in st.session_state:
        st.success(f"✅ {st.session_state.pop('registration_success_message')}")

    with st.form("geometric_auth_gate", clear_on_submit=False):
        st.markdown(
            "<h3 style='margin-top:0; font-family:sans-serif; font-weight:700; color:#372713;'>Account Sign In</h3>", 
            unsafe_allow_html=True
        )
        render_dev_mode_banner()
        st.write("")

        email = st.text_input("Email Address", placeholder="name@domain.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
        st.markdown(
            '<p style="text-align:right; margin-top:-0.5rem;"><a href="#" style="color:#A99670; font-weight:600; font-size:0.85rem; text-decoration:none;">Forgot Password?</a></p>',
            unsafe_allow_html=True,
        )
        
        st.write("")
        login_clicked = st.form_submit_button("Sign In", use_container_width=True)
        
        st.write(" ")
        nav_left, nav_right = st.columns([1, 1.2])
        with nav_left:
            st.markdown('<p style="text-align:right; margin-top:0.4rem; font-size:0.9rem; color:#64748B;">New to GrocEase?</p>', unsafe_allow_html=True)
        with nav_right:
            st.page_link("pages/02_Create_Account.py", label="Create Household Account")

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
