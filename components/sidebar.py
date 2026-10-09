"""
components/sidebar.py
=====================
GrocEase sidebar navigation component.

Renders the branded sidebar with:
- Browser-style Back and Forward navigation controls
- Logo / user greeting
- Interactive joined room switcher dropdown
- Page navigation links
- Logout button

Usage:
    from components.sidebar import render_sidebar, render_room_selector
    render_sidebar()
"""

import streamlit as st
from utils.session import (
    get_username,
    get_current_user_id,
    get_current_room_id,
    get_current_room_name,
    set_current_room,
)


# Navigation items: (label, emoji, page_path)
NAV_ITEMS = [
    ("Dashboard",         "📊", "pages/06_Dashboard.py"),
    ("Rooms",             "🏠", "pages/07_Rooms.py"),
    ("Grocery List",      "🛒", "pages/08_Grocery_List.py"),
    ("Shopping",          "🧺", "pages/09_Shopping.py"),
    ("Bill Scanning",     "📷", "pages/10_Bill_Scanning.py"),
    ("Payments",          "💳", "pages/11_Payments.py"),
    ("Personal Expenses", "📝", "pages/12_Personal_Expenses.py"),
    ("Budget",            "🎯", "pages/13_Budget.py"),
    ("Profile",           "👤", "pages/14_Profile.py"),
]

_SIDEBAR_CSS = """
<style>
/* Hide Streamlit's auto-generated multipage nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* Sidebar base */
[data-testid="stSidebar"] {
    background-color: #1F4C3D !important;
    min-width: 230px !important;
}
[data-testid="stSidebar"] * {
    color: #F6F2E9 !important;
}



/* Sidebar logo */
.sb-logo {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #F6F2E9;
    letter-spacing: -0.02em;
    margin-bottom: 0.1rem;
}
.sb-tagline {
    font-size: 0.76rem;
    color: #C3D6C6;
    margin-bottom: 1.2rem;
}
.sb-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.15);
    margin: 0.8rem 0;
}
.sb-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #C3D6C6;
    margin: 0.9rem 0 0.3rem 0;
}
.sb-user-chip {
    background: rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.83rem;
    font-weight: 600;
    color: #F6F2E9;
    display: inline-block;
    margin-bottom: 0.4rem;
}

/* Sidebar selectbox styling for rooms */
[data-testid="stSidebar"] [data-baseweb="select"] {
    background-color: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #F6F2E9 !important;
}

/* Nav links in sidebar */
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    color: #E7EFE6 !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    padding: 6px 0 !important;
    display: block;
    text-decoration: none !important;
    border-radius: 4px;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
    color: #E7EFE6 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p {
    color: #FFFFFF !important;
    text-decoration: underline !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background-color: transparent !important;
    color: #F6F2E9 !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.8rem !important;
    width: 100%;
    text-align: left;
    margin-top: 0.3rem;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255,255,255,0.1) !important;
}
</style>
"""


def _get_available_rooms(user_id: int) -> list:
    """Fetch joined rooms from DB."""
    try:
        from database.database import get_user_joined_rooms
        return get_user_joined_rooms(user_id) or []
    except Exception:
        return []


def render_room_selector(key_prefix: str = "global"):
    """
    Renders an interactive, universal Room Selection dropdown anywhere on a page.
    Automatically keeps active room in sync across pages.
    """
    user_id = get_current_user_id()
    rooms = _get_available_rooms(user_id)
    if not rooms:
        st.info("🏠 You have not joined any rooms yet. Visit **Rooms** to create or join one.")
        return None

    room_map = {f"{r['name']} ({r.get('secret_code') or r.get('code', '')})": r for r in rooms}
    current_id = get_current_room_id()

    cur_idx = 0
    options = list(room_map.keys())
    for i, (label, r) in enumerate(room_map.items()):
        if r["id"] == current_id:
            cur_idx = i
            break
    else:
        # If no room was active, default to first room
        first_r = rooms[0]
        set_current_room(first_r["id"], first_r["name"])
        cur_idx = 0

    selected_label = st.selectbox(
        "🏠 Active Room",
        options=options,
        index=cur_idx,
        key=f"{key_prefix}_room_dropdown",
    )

    selected_room = room_map[selected_label]
    if selected_room["id"] != get_current_room_id():
        set_current_room(selected_room["id"], selected_room["name"])
        st.rerun()

    return selected_room


def render_sidebar():
    """
    Render the GrocEase sidebar navigation.
    Call this at the top of every protected page.
    """
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    with st.sidebar:
        # ── Logo ──────────────────────────────────────
        st.markdown(
            '<div class="sb-logo">🛒 GrocEase</div>'
            '<div class="sb-tagline">Shop together. Split smarter.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── User chip ─────────────────────────────────
        username = get_username()
        st.markdown(
            f'<div class="sb-user-chip">👤 {username}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Navigation Links ──────────────────────────
        st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)

        for label, emoji, path in NAV_ITEMS:
            st.page_link(path, label=f"{emoji}  {label}")

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Logout ────────────────────────────────────
        if st.button("🚪  Logout", key="sidebar_logout_btn"):
            st.switch_page("pages/05_Logout.py")
