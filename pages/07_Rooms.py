"""
pages/07_Rooms.py
=================
Rooms page — create, join, view, and leave rooms.
Queries the database to display actual usernames and nicknames of members in created rooms.
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
from components.alerts import confirmation_dialog
from database.database import (
    get_user_joined_rooms,
    get_room_members_with_identities,
)
from services.room_service import (
    create_room as svc_create_room,
    join_room as svc_join_room,
    leave_room as svc_leave_room,
)
from mock.mock_api import (
    get_rooms as mock_get_rooms,
    create_room as mock_create_room,
    join_room as mock_join_room,
    leave_room as mock_leave_room,
    get_room_members as mock_get_room_members,
)
from mock.mock_data import get_username as mock_get_username

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
st.markdown("<p style='color:#5B6459; margin-top:-0.8rem;'>Create and manage shared spaces for your grocery groups.</p>", unsafe_allow_html=True)
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
                res = svc_create_room(user_id, room_name.strip())
                if res and res.get("success"):
                    created_room = res["data"]
                    room_display_code = created_room.get("secret_code") or created_room.get("code", "")
                    st.success(f"✅ Room **{created_room['name']}** created successfully!")
                    st.markdown(
                        f"""
                        <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px;
                                    padding:1rem 1.4rem; margin-top:0.5rem;">
                            <div style="font-size:0.85rem; color:#5B6459; margin-bottom:0.3rem;">Share this secret code with your group to join:</div>
                            <div style="font-family:'Fraunces',serif; font-size:2rem; font-weight:700;
                                        color:#1F4C3D; letter-spacing:0.08em;">{room_display_code}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    set_current_room(created_room["id"], created_room["name"])
                    st.rerun()
                else:
                    err_msg = res.get("message") if res else "Could not create room."
                    st.error(f"❌ {err_msg}")

with tab_join:
    st.markdown("#### Join an existing room using a code")
    with st.form("join_room_form", clear_on_submit=True):
        room_code = st.text_input("Room code", placeholder="e.g. HG-4821")
        if st.form_submit_button("Join Room", type="primary"):
            if not room_code.strip():
                st.error("Please enter a room code.")
            else:
                code_clean = room_code.strip().upper()
                res = svc_join_room(user_id, code_clean)
                if res and res.get("success"):
                    joined_room = res["data"]
                    st.success(f"✅ Joined **{joined_room['name']}**!")
                    set_current_room(joined_room["id"], joined_room["name"])
                    st.rerun()
                else:
                    err_msg = res.get("message") if res else "Invalid room code, or you are already a member of this room."
                    st.error(f"❌ {err_msg}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Rooms retrieval ───────────────────────────────────────────────────────────
db_rooms = get_user_joined_rooms(user_id)
rooms = [
    {
        "id": r["id"],
        "name": r["name"],
        "creatorId": user_id if r.get("role") == "creator" else 0,
        "createdAt": str(r.get("created_at") or ""),
        "code": r.get("secret_code", ""),
        "role": r.get("role", "member"),
    }
    for r in db_rooms
]

# ── Split into Created Rooms and Joined Rooms ─────────────────────────────────
created_rooms = [r for r in rooms if r.get("creatorId") == user_id or r.get("role") == "creator"]
joined_rooms = [r for r in rooms if r not in created_rooms]

st.markdown("### 👑 Created Rooms")
if not created_rooms:
    st.info("You haven't created any rooms yet. Use the Create Room tab above to start one!")
else:
    for room in created_rooms:
        # Query database for actual member identities
        db_members = get_room_members_with_identities(room["id"])
        members_list = [
            {
                "name": m.get("display_name") or m.get("actual_name") or f"User {m['user_id']}",
                "role": m.get("role", "member"),
            }
            for m in db_members
        ]

        member_count = len(members_list)
        with st.expander(f"🏠 {room['name']}  —  {member_count} member{'s' if member_count != 1 else ''}", expanded=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                code_val = room.get("code") or room.get("secret_code", "")
                created_val = format_datetime(room["createdAt"]) if room.get("createdAt") else "Recent"
                st.markdown(
                    f"""
                    <div style="font-size:0.88rem; color:#5B6459; margin-bottom:0.8rem;">
                        <strong>Room Code:</strong> <code>{code_val}</code> &nbsp;|&nbsp;
                        <strong>Your Role:</strong> {badge_html("creator")} &nbsp;|&nbsp;
                        <strong>Created:</strong> {created_val}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("**Room Members (Identity & Nicknames):**")
                for m in members_list:
                    st.markdown(
                        f"&nbsp;&nbsp; {badge_html(m['role'])} &nbsp; <strong>{m['name']}</strong>",
                        unsafe_allow_html=True,
                    )

            with col_actions:
                if st.button("📋 Open List", key=f"created_open_list_{room['id']}", type="primary"):
                    set_current_room(room["id"], room["name"])
                    st.switch_page("pages/08_Grocery_List.py")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 🤝 Joined Rooms")

if not joined_rooms:
    st.info("You haven't joined other members' rooms yet.")
else:
    for room in joined_rooms:
        db_members = get_room_members_with_identities(room["id"])
        members_list = [
            {
                "name": m.get("display_name") or m.get("actual_name") or f"User {m['user_id']}",
                "role": m.get("role", "member"),
            }
            for m in db_members
        ]

        member_count = len(members_list)
        with st.expander(f"🏠 {room['name']}  —  {member_count} member{'s' if member_count != 1 else ''}"):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                code_val = room.get("code") or room.get("secret_code", "")
                created_val = format_datetime(room["createdAt"]) if room.get("createdAt") else "Recent"
                st.markdown(
                    f"""
                    <div style="font-size:0.88rem; color:#5B6459; margin-bottom:0.8rem;">
                        <strong>Room Code:</strong> <code>{code_val}</code> &nbsp;|&nbsp;
                        <strong>Your Role:</strong> {badge_html('member')} &nbsp;|&nbsp;
                        <strong>Created:</strong> {created_val}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("**Room Members:**")
                for m in members_list:
                    st.markdown(
                        f"&nbsp;&nbsp; {badge_html(m['role'])} &nbsp; <strong>{m['name']}</strong>",
                        unsafe_allow_html=True,
                    )

            with col_actions:
                if st.button("📋 Open List", key=f"joined_open_list_{room['id']}"):
                    set_current_room(room["id"], room["name"])
                    st.switch_page("pages/08_Grocery_List.py")

                leave_key = f"confirm_leave_{room['id']}"
                if st.session_state.get(leave_key, False):
                    result = confirmation_dialog(
                        key=f"leave_dlg_{room['id']}",
                        prompt=f"Leave **{room['name']}**? This cannot be undone.",
                        confirm_label="Yes, Leave",
                        cancel_label="Cancel",
                    )
                    if result is True:
                        try:
                            svc_leave_room(user_id, room["id"])
                        except Exception:
                            mock_leave_room(room["id"], user_id)
                        st.session_state[leave_key] = False
                        st.success("Left the room.")
                        st.rerun()
                    elif result is False:
                        st.session_state[leave_key] = False
                        st.rerun()
                else:
                    with st.container():
                        st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
                        if st.button("🚪 Leave Room", key=f"leave_btn_{room['id']}"):
                            st.session_state[leave_key] = True
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
