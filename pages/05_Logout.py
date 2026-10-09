import streamlit as st
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import logout_user

# Cleanly revoke session token and clear auth state immediately
logout_user()

from style import apply_base_style, top_nav, hide_sidebar

st.set_page_config(
    page_title="Logout — GrocEase",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_base_style()
hide_sidebar()
top_nav()

# Check if redirected here due to timeout
session_expired = st.session_state.pop("session_expired", False)

st.markdown(
    """
    <h2 style="text-align:center; margin-bottom:0.2rem;">Logged Out</h2>
    <p class="groc-muted" style="text-align:center; margin-bottom:1.6rem;">
    Thank you for using GrocEase!
    </p>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([0.2, 3, 0.2])
with mid:
    st.markdown('<div class="groc-card">', unsafe_allow_html=True)
    if session_expired:
        st.warning("⏱️ You were automatically logged out due to inactivity.")
    else:
        st.success("👋 You have been successfully logged out.")
    
    st.write("")
    if st.button("Back to Login", type="primary", use_container_width=True):
        st.switch_page("pages/01_Login.py")
    st.markdown('</div>', unsafe_allow_html=True)