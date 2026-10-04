"""
pages/14_Profile.py
====================
User profile page — view and mock-edit profile details.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_username
from utils.formatting import format_datetime
from components.sidebar import render_sidebar
from components.cards import render_metric_card
from mock.mock_api import get_rooms, get_personal_expenses, get_budgets
from mock.mock_data import MOCK_CURRENT_USER

st.set_page_config(
    page_title="Profile — GrocEase",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id  = get_current_user_id()
username = get_username()

st.markdown("# 👤 My Profile")
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Profile card ──────────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    # Avatar placeholder
    st.markdown(
        f"""
        <div style="background:#1F4C3D; color:#F6F2E9; border-radius:50%;
                    width:90px; height:90px; display:flex; align-items:center;
                    justify-content:center; font-family:'Fraunces',serif;
                    font-size:2.5rem; font-weight:700; margin-bottom:1rem;">
            {username[0].upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_email = st.session_state.get("user_email", MOCK_CURRENT_USER["email"])
    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-family:'Fraunces',serif; font-size:1.4rem; font-weight:600;
                        color:#1F4C3D;">{username}</div>
            <div style="font-size:0.88rem; color:#5B6459;">{user_email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stats
    rooms    = get_rooms(user_id)
    expenses = get_personal_expenses(user_id)
    budgets  = get_budgets(user_id)

    st.markdown("<br>", unsafe_allow_html=True)
    render_metric_card("Rooms Joined",   str(len(rooms)))
    render_metric_card("Total Expenses", str(len(expenses)))
    render_metric_card("Budgets Set",    str(len(budgets)))

with right_col:
    st.markdown("### Account Details")

    # Display only (edit would call real backend)
    with st.form("profile_view_form"):
        display_name = st.text_input("Display name", value=username, disabled=True)
        email        = st.text_input("Email", value=user_email, disabled=True)
        st.caption("To update your profile details, please contact support (backend integration pending).")
        st.form_submit_button("Update Profile", disabled=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Recent Rooms")

    if not rooms:
        st.info("You haven't joined any rooms yet.")
    else:
        for room in rooms:
            role = "Creator" if room["creatorId"] == user_id else "Member"
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #D8D0BE;
                            border-left:4px solid #1F4C3D; border-radius:6px;
                            padding:0.7rem 1rem; margin-bottom:0.5rem;">
                    <div style="font-weight:600; color:#20261F;">{room['name']}</div>
                    <div style="font-size:0.8rem; color:#5B6459;">
                        Code: <code>{room['code']}</code> &nbsp;|&nbsp; Role: {role}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Danger Zone")
    st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
    if st.button("🚪 Logout", key="profile_logout"):
        st.switch_page("pages/05_Logout.py")
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("To permanently delete your account, use the login page after logging out.")
