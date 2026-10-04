"""
pages/07_Rooms.py
=================
Rooms page — create, join, view, and leave rooms.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, set_current_room, clear_current_room
from utils.formatting import format_datetime, badge_html
from components.sidebar import render_sidebar
from components.cards import render_empty_state
from components.alerts import success_alert, error_alert, confirmation_dialog
from mock.mock_api import (
    get_rooms,
    create_room,
    join_room,
    leave_room,
    get_room_members,
)
from mock.mock_data import get_username

st.set_page_config(
    page_title="Rooms — GrocEase",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id = get_current_user_id()

st.markdown("# 🏠 Rooms")
st.markdown("<p style='color:#5B6459; margin-top:-0.8rem;'>Create shared spaces for your grocery groups.</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Create / Join tabs ────────────────────────────────────────────────────────
tab_create, tab_join = st.tabs(["➕ Create Room", "🔗 Join Room"])

with tab_create:
    st.markdown("#### Create a new shared grocery room")
    with st.form("create_room_form", clear_on_submit=True):
        room_name = st.text_input("Room name", placeholder="e.g. Home Grocery")
        if st.form_submit_button("Create Room", type="primary"):
            if not room_name.strip():
                st.error("Please enter a room name.")
            else:
                new_room = create_room(room_name.strip(), user_id)
                st.success(f"✅ Room **{new_room['name']}** created!")
                st.markdown(
                    f"""
                    <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px;
                                padding:1rem 1.4rem; margin-top:0.5rem;">
                        <div style="font-size:0.85rem; color:#5B6459; margin-bottom:0.3rem;">Share this code with your group:</div>
                        <div style="font-family:'Fraunces',serif; font-size:2rem; font-weight:700;
                                    color:#1F4C3D; letter-spacing:0.08em;">{new_room['code']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with tab_join:
    st.markdown("#### Join an existing room using a code")
    with st.form("join_room_form", clear_on_submit=True):
        room_code = st.text_input("Room code", placeholder="e.g. HG-4821")
        if st.form_submit_button("Join Room", type="primary"):
            if not room_code.strip():
                st.error("Please enter a room code.")
            else:
                joined = join_room(room_code.strip().upper(), user_id)
                if joined:
                    st.success(f"✅ Joined **{joined['name']}**!")
                else:
                    st.error("Invalid room code, or you are already a member of this room.")

st.markdown("<br>", unsafe_allow_html=True)

# ── My Rooms list ─────────────────────────────────────────────────────────────
st.markdown("### My Rooms")

rooms = get_rooms(user_id)

if not rooms:
    render_empty_state("🏠", "You haven't joined any rooms yet", "Create or join a room to get started.")
else:
    for room in rooms:
        members = get_room_members(room["id"])
        member_count = len(members)
        is_creator = room["creatorId"] == user_id
        role_label = "Creator" if is_creator else "Member"

        with st.expander(f"🏠 {room['name']}  —  {member_count} member{'s' if member_count != 1 else ''}"):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(
                    f"""
                    <div style="font-size:0.88rem; color:#5B6459; margin-bottom:0.8rem;">
                        <strong>Room Code:</strong> <code>{room['code']}</code> &nbsp;|&nbsp;
                        <strong>Your Role:</strong> {badge_html(role_label.lower())}
                        &nbsp;|&nbsp; <strong>Created:</strong> {format_datetime(room['createdAt'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("**Members:**")
                for m in members:
                    uname = get_username(m["userId"])
                    st.markdown(
                        f"&nbsp;&nbsp; {badge_html(m['role'])} &nbsp; {uname}",
                        unsafe_allow_html=True,
                    )

            with col_actions:
                if st.button("📋 Open List", key=f"open_list_{room['id']}"):
                    set_current_room(room["id"], room["name"])
                    st.switch_page("pages/08_Grocery_List.py")

                # Leave room (non-creators can always leave; creators need confirmation)
                leave_key = f"confirm_leave_{room['id']}"
                if st.session_state.get(leave_key, False):
                    result = confirmation_dialog(
                        key=f"leave_dlg_{room['id']}",
                        prompt=f"Leave **{room['name']}**? This cannot be undone.",
                        confirm_label="Yes, Leave",
                        cancel_label="Cancel",
                    )
                    if result is True:
                        leave_room(room["id"], user_id)
                        st.session_state[leave_key] = False
                        st.success("Left the room.")
                        st.rerun()
                    elif result is False:
                        st.session_state[leave_key] = False
                        st.rerun()
                else:
                    if not is_creator:
                        with st.container():
                            st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
                            if st.button("🚪 Leave Room", key=f"leave_btn_{room['id']}"):
                                st.session_state[leave_key] = True
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.caption("You are the creator.")
